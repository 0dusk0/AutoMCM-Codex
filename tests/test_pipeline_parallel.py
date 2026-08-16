from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ParallelPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="automcm-test-")
        self.workspace = Path(self.temp.name)
        shutil.copytree(ROOT / "scripts", self.workspace / "scripts")
        shutil.copytree(ROOT / "templates", self.workspace / "templates")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_python(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, *args],
            cwd=self.workspace,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            expected,
            result.returncode,
            msg=f"command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def test_parallel_build_and_verify_do_not_regress_approved_stages(self) -> None:
        self.run_python("scripts/setup_workspace.py", "--mode", "cumcm")
        self.run_python(
            "scripts/pipeline_manager.py",
            "init",
            "--mode",
            "AP",
            "--contest",
            "CUMCM",
            "--problems",
            "2",
        )
        self.run_python("scripts/pipeline_manager.py", "advance", "problem_analysis")
        self.run_python("scripts/pipeline_manager.py", "advance", "data_preprocessing")

        build_wave = self.run_python("scripts/pipeline_manager.py", "suggest-parallel")
        self.assertEqual("model_1_build model_2_build", build_wave.stdout.strip())
        self.run_python(
            "scripts/pipeline_manager.py",
            "parallel-start",
            "model_1_build",
            "model_2_build",
        )
        self.run_python("scripts/pipeline_manager.py", "advance", "model_1_build")
        self.run_python("scripts/pipeline_manager.py", "advance", "model_2_build")

        verify_wave = self.run_python("scripts/pipeline_manager.py", "suggest-parallel")
        self.assertEqual("model_1_verify model_2_verify", verify_wave.stdout.strip())
        self.run_python(
            "scripts/pipeline_manager.py",
            "parallel-start",
            "model_1_verify",
            "model_2_verify",
        )
        self.run_python("scripts/pipeline_manager.py", "advance", "model_1_verify")
        self.run_python("scripts/pipeline_manager.py", "advance", "model_2_verify")
        self.run_python(
            "scripts/pipeline_manager.py",
            "parallel-all-done",
            "model_1_verify",
            "model_2_verify",
        )

        state = json.loads(
            (self.workspace / "CUMCM_Workspace/state/pipeline.json").read_text(encoding="utf-8")
        )
        for stage in ("model_1_build", "model_2_build", "model_1_verify", "model_2_verify"):
            self.assertEqual("approved", state["stages"][stage]["status"])
        self.assertEqual("sensitivity_analysis", state["current_stage"])
        self.assertNotIn("model_3_build", state["stages"])

    def test_numerical_sanity_fails_when_output_artifact_is_missing(self) -> None:
        result = self.run_python(
            "scripts/quality_gate.py",
            "sanity",
            "--stage",
            "model_1_build",
            "--output-file",
            "missing-output.txt",
            expected=1,
        )
        self.assertIn("不存在", result.stdout)

    def test_documented_verification_report_format_is_accepted(self) -> None:
        report = self.workspace / "verify-report.txt"
        report.write_text(
            "========== VERIFICATION REPORT ==========\n"
            "Stage  : model_1_verify\n"
            "Result : PASS\n"
            "Checks :\n"
            "  [V-1] ✓ PASS  constraints satisfied\n"
            "==========================================\n",
            encoding="utf-8",
        )
        result = self.run_python(
            "scripts/quality_gate.py",
            "verify",
            "--stage",
            "model_1_verify",
            "--report-file",
            str(report),
        )
        self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
