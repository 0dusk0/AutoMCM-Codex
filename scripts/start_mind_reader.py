#!/usr/bin/env python3
"""Start the AutoMCM Mind-Reader UI as a local background service."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "docker" / "mind-reader"
WORKSPACE = ROOT / "CUMCM_Workspace"
HEALTH_URL = "http://127.0.0.1:8080/health"


def server_python() -> Path:
    if os.name == "nt":
        venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = ROOT / ".venv" / "bin" / "python"
    return venv_python if venv_python.is_file() else Path(sys.executable)


def is_healthy(timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def dependency_error(python_executable: Path) -> str | None:
    check = subprocess.run(
        [
            str(python_executable),
            "-c",
            "import fastapi, uvicorn, watchdog, aiofiles",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if check.returncode == 0:
        return None
    return (
        "缺少 Mind-Reader 依赖。请运行：python -m venv .venv && "
        ".venv/Scripts/python -m pip install -r docker/mind-reader/requirements.txt"
    )


def start_background(wait_seconds: float = 12.0) -> int:
    if is_healthy():
        print("[mind-reader] 已运行：http://localhost:8080")
        return 0

    python_executable = server_python()
    error = dependency_error(python_executable)
    if error:
        print(f"[mind-reader] {error}", file=sys.stderr)
        return 2

    diagnostics = WORKSPACE / "output" / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    log_path = diagnostics / "mind_reader.log"

    environment = os.environ.copy()
    environment.update(
        {
            "THOUGHT_FILE": str(WORKSPACE / "memory" / "thought_process.md"),
            "EVAL_FILE": str(WORKSPACE / "memory" / "evaluation_log.md"),
            "ITERATION_FILE": str(WORKSPACE / "memory" / "iteration.json"),
            "PIPELINE_FILE": str(WORKSPACE / "state" / "pipeline.json"),
            "REVIEW_FILE": str(WORKSPACE / "state" / "review_request.md"),
            "HUMAN_FILE": str(WORKSPACE / "state" / "human_intervention.md"),
            "WORKSPACE_DIR": str(WORKSPACE),
            "PYTHONUNBUFFERED": "1",
        }
    )

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

    with log_path.open("ab") as log_stream:
        process = subprocess.Popen(
            [str(python_executable), "server.py"],
            cwd=SERVER_DIR,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            print(f"[mind-reader] 启动失败，请查看日志：{log_path}", file=sys.stderr)
            return 1
        if is_healthy():
            print(f"[mind-reader] 已启动：http://localhost:8080（PID {process.pid}）")
            return 0
        time.sleep(0.25)

    print(f"[mind-reader] 启动超时，请查看日志：{log_path}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="仅检查服务健康状态")
    args = parser.parse_args()
    if args.check:
        if is_healthy():
            print("[mind-reader] healthy：http://localhost:8080")
            return 0
        print("[mind-reader] unavailable：http://localhost:8080", file=sys.stderr)
        return 1
    return start_background()


if __name__ == "__main__":
    raise SystemExit(main())
