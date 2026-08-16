from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location("automcm_draw_image", SCRIPTS / "draw_image.py")
assert SPEC and SPEC.loader
draw_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(draw_image)


class ModelInvocationRulesTest(unittest.TestCase):
    def test_images_api_auth_is_not_inferred_from_codex_cli(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            auth = draw_image.check_auth()
        self.assertFalse(auth["available"])
        self.assertEqual("none", auth["method"])

    def test_api_key_enables_only_the_images_api_path(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-placeholder"}, clear=True):
            auth = draw_image.check_auth()
        self.assertTrue(auth["available"])
        self.assertEqual("api_key", auth["method"])

    def test_image_model_resolution_is_separate_and_predictable(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("gpt-image-2", draw_image.resolve_image_model(None))
        with patch.dict(os.environ, {"AUTOMCM_IMAGE_MODEL": "gpt-image-1"}, clear=True):
            self.assertEqual("gpt-image-1", draw_image.resolve_image_model(None))
            self.assertEqual("gpt-image-2", draw_image.resolve_image_model("gpt-image-2"))
        with self.assertRaises(ValueError):
            draw_image.resolve_image_model("dall-e-3")

    def test_check_command_fails_closed_without_api_key(self) -> None:
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "draw_image.py"), "--check"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("method=none", result.stdout)

    def test_no_key_generation_writes_python_fallback_at_workspace_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "CUMCM_Workspace"
            output = workspace / "latex" / "images" / "fig_pipeline.png"
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "draw_image.py"),
                    "--prompt",
                    "流程图：读取题目到生成 PDF",
                    "--output",
                    str(output),
                    "--fallback",
                    "python",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            fallback = workspace / "src" / "figures" / "fig_pipeline.py"
            self.assertEqual(2, result.returncode)
            self.assertTrue(fallback.is_file())
            content = fallback.read_text(encoding="utf-8")
            self.assertIn("流程图：读取题目到生成 PDF", content)
            self.assertIn(repr(str(output)), content)
            self.assertFalse(output.exists(), "fallback scaffold must not masquerade as a final image")
            compile_result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(fallback)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, compile_result.returncode, compile_result.stderr)

    def test_comment_and_matlab_fallbacks_are_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matlab = root / "figure.m"
            comment = root / "figure.tex"
            draw_image.write_fallback("需求 A", "figure.png", "matlab", str(matlab))
            draw_image.write_fallback("需求 B", "figure.png", "comment", str(comment))
            self.assertIn("TODO", matlab.read_text(encoding="utf-8"))
            self.assertIn("\\missingfigure", comment.read_text(encoding="utf-8"))

            matlab.write_text("% user implementation\n", encoding="utf-8")
            draw_image.write_fallback("新需求", "figure.png", "matlab", str(matlab))
            self.assertEqual("% user implementation\n", matlab.read_text(encoding="utf-8"))

    def test_launchers_keep_codex_model_override_outside_image_script(self) -> None:
        for name in ("start_modeling.sh", "init_gitops.sh"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("AUTOMCM_CODEX_MODEL", text)
            self.assertIn("--model", text)
            self.assertIn("resolve_codex_cli", text)
            self.assertIn('"$CODEX_CLI" "${CODEX_ARGS[@]}"', text)
        image_script = (SCRIPTS / "draw_image.py").read_text(encoding="utf-8")
        self.assertIn("AUTOMCM_IMAGE_MODEL", image_script)
        self.assertNotIn("AUTOMCM_CODEX_MODEL", image_script)

    def test_codex_resolver_supports_windows_desktop_app(self) -> None:
        resolver = (SCRIPTS / "codex_cli.sh").read_text(encoding="utf-8")
        self.assertIn("command -v codex", resolver)
        self.assertIn("Get-AppxPackage -Name OpenAI.Codex", resolver)
        self.assertIn("app\\\\resources\\\\codex.exe", resolver)
        self.assertIn('[[ -f "${candidate}.exe" ]]', resolver)
        self.assertIn("cygpath -u", resolver)

    def test_gitops_resolves_codex_before_initializing_pipeline(self) -> None:
        launcher = (ROOT / "init_gitops.sh").read_text(encoding="utf-8")
        self.assertLess(
            launcher.index('CODEX_CLI="$(resolve_codex_cli)"'),
            launcher.index("python scripts/setup_workspace.py"),
        )

    def test_launchers_start_mind_reader_after_workspace_setup(self) -> None:
        for name in ("start_modeling.sh", "init_gitops.sh"):
            launcher = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("python scripts/start_mind_reader.py", launcher)
            self.assertLess(
                launcher.index("python scripts/setup_workspace.py"),
                launcher.index("python scripts/start_mind_reader.py"),
            )


if __name__ == "__main__":
    unittest.main()
