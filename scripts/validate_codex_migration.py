#!/usr/bin/env python3
"""Validate the AutoMCM-Pro OpenAI Codex migration without extra packages."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_NAMES = ("auto-mcm", "cumcm-master", "mcm-master", "draw-image")
ENGINEERING_FILES = (
    "AutoMCM_SOP.md",
    "scripts/pipeline_manager.py",
    "scripts/quality_gate.py",
    "scripts/security_check.py",
    "scripts/contest_git.py",
    "scripts/compile_pdf.py",
    "scripts/setup_workspace.py",
    "scripts/console_utils.py",
    "templates/latex_template.tex",
    "templates/mcm_template.tex",
    "templates/mcm_memo_template.tex",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    if (ROOT / ".claude").exists():
        failures.append("legacy .claude directory still exists")

    for relative in ("AGENTS.md", *ENGINEERING_FILES):
        if not (ROOT / relative).is_file():
            failures.append(f"missing required engineering file: {relative}")

    for name in SKILL_NAMES:
        skill_dir = ROOT / ".codex" / "skills" / name
        skill_md = skill_dir / "SKILL.md"
        openai_yaml = skill_dir / "agents" / "openai.yaml"

        if not skill_md.is_file():
            failures.append(f"missing Skill: {skill_md.relative_to(ROOT)}")
            continue
        if not openai_yaml.is_file():
            failures.append(f"missing Codex metadata: {openai_yaml.relative_to(ROOT)}")

        text = skill_md.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not match:
            failures.append(f"invalid frontmatter: {skill_md.relative_to(ROOT)}")
        else:
            frontmatter = match.group(1)
            if not re.search(rf"(?m)^name:\s*{re.escape(name)}\s*$", frontmatter):
                failures.append(f"wrong Skill name in {skill_md.relative_to(ROOT)}")
            if not re.search(r"(?m)^description:\s*", frontmatter):
                failures.append(f"missing description in {skill_md.relative_to(ROOT)}")

        if openai_yaml.is_file():
            metadata = openai_yaml.read_text(encoding="utf-8")
            if f"${name}" not in metadata:
                failures.append(f"default_prompt does not mention ${name}: {openai_yaml.relative_to(ROOT)}")

    live_files = (
        "AGENTS.md",
        "AutoMCM_SOP.md",
        "README.md",
        "install.sh",
        "uninstall.sh",
        "start_modeling.sh",
        "init_gitops.sh",
        ".codex/skills/auto-mcm/SKILL.md",
        ".codex/skills/cumcm-master/SKILL.md",
        ".codex/skills/mcm-master/SKILL.md",
    )
    forbidden = {
        "Claude Code": "Claude-specific product reference",
        "claude --print": "Claude launcher",
        "AskUserQuestion": "Claude-only interaction primitive",
        "TodoWrite": "Claude-only task primitive",
        "Agent(description=": "Claude-style subagent syntax",
        "/auto-mcm": "slash-style AutoMCM invocation",
        "/cumcm-master": "slash-style CUMCM invocation",
        "/mcm-master": "slash-style MCM invocation",
        "/draw-image": "slash-style image invocation",
    }
    for relative in live_files:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for needle, label in forbidden.items():
            if needle in text:
                failures.append(f"{label} remains in {relative}: {needle}")

    launchers = read("start_modeling.sh") + read("init_gitops.sh")
    if "codex" not in launchers or "exec --sandbox workspace-write" not in launchers:
        failures.append("launcher does not use codex exec with workspace-write sandbox")

    draw_image = read("scripts/draw_image.py")
    for secret_probe in (
        "auth.json",
        "CODEX_AUTH_TOKEN",
        "OPENAI_OAUTH_TOKEN",
        "_CODEX_AUTH_PATHS",
        'shutil.which("codex")',
        '"codex_native"',
    ):
        if secret_probe in draw_image:
            failures.append(f"draw_image.py still infers Images API access from Codex state: {secret_probe}")

    if "AUTOMCM_IMAGE_MODEL" not in draw_image or 'DEFAULT_IMAGE_MODEL = "gpt-image-2"' not in draw_image:
        failures.append("draw_image.py does not isolate Images API model selection")
    if '"dall-e-3"' in draw_image or '"dall-e-2"' in draw_image:
        failures.append("draw_image.py still exposes DALL-E through GPT Image request parameters")
    for fallback_marker in ("write_fallback", "AUTOMCM_IMAGE_FALLBACK", 'FALLBACK_KINDS = ("python", "matlab", "comment")'):
        if fallback_marker not in draw_image:
            failures.append(f"draw_image.py is missing mandatory no-key fallback: {fallback_marker}")

    draw_skill = read(".codex/skills/draw-image/SKILL.md")
    for required_rule in ("--fallback python", "--fallback matlab", "--fallback comment", "不得静默"):
        if required_rule not in draw_skill:
            failures.append(f"draw-image Skill is missing no-key behavior: {required_rule}")

    agents_md = read("AGENTS.md")
    if "OPENAI_API_KEY" not in agents_md or "Python/MATLAB" not in agents_md or "不得静默" not in agents_md:
        failures.append("AGENTS.md does not enforce the no-key figure fallback")

    for launcher in ("start_modeling.sh", "init_gitops.sh"):
        text = read(launcher)
        if "AUTOMCM_CODEX_MODEL" not in text or "--model" not in text:
            failures.append(f"{launcher} does not expose the Codex-only model override")

    if failures:
        print("Codex migration validation: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Codex migration validation: PASS")
    print(f"  Skills: {', '.join(SKILL_NAMES)}")
    print(f"  Engineering files preserved: {len(ENGINEERING_FILES)}")
    print("  Shared pipeline state is assigned to the main Codex agent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
