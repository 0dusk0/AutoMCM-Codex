"""Independent checks for the problem-1 spiral kinematics output."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "src" / "models" / "problem1_spiral.py"
RESULT_PATH = ROOT / "output" / "result1.xlsx"


def load_model():
    spec = importlib.util.spec_from_file_location("problem1_spiral", MODEL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load model from {MODEL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_schema_and_rows(df: pd.DataFrame, cfg) -> tuple[bool, str]:
    required = {
        "time_s", "handle_id", "label", "x_m", "y_m", "vx_mps", "vy_mps", "speed_mps"
    }
    expected_rows = (cfg.duration + 1) * (cfg.bench_count + 1)
    ok = required.issubset(df.columns) and len(df) == expected_rows
    return ok, f"columns={len(df.columns)}, rows={len(df)} expected={expected_rows}"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    model = load_model()
    cfg = model.Config()
    try:
        df = pd.read_excel(RESULT_PATH, sheet_name="all_handles")
        ok, detail = check_schema_and_rows(df, cfg)
        checks.append(("V-KIN-1", ok, detail))

        numeric = df[["x_m", "y_m", "vx_mps", "vy_mps", "speed_mps"]].to_numpy(float)
        finite = bool(np.isfinite(numeric).all())
        checks.append(("V-KIN-2", finite, "all numeric output values are finite"))

        max_spacing_error = 0.0
        for time_s, group in df.groupby("time_s", sort=True):
            group = group.sort_values("handle_id")
            points = group[["x_m", "y_m"]].to_numpy(float)
            spacings = np.linalg.norm(np.diff(points, axis=0), axis=1)
            target = np.array([cfg.head_spacing] + [cfg.regular_spacing] * (cfg.bench_count - 1))
            max_spacing_error = max(max_spacing_error, float(np.max(np.abs(spacings - target))))
        ok = max_spacing_error < 1e-8
        checks.append(("V-KIN-3", ok, f"max chord residual={max_spacing_error:.3e} m"))

        head = df[df["handle_id"] == 0].sort_values("time_s")
        head_speed_error = float(np.max(np.abs(head["speed_mps"].to_numpy() - cfg.head_speed)))
        ok = head_speed_error < 1e-10
        checks.append(("V-KIN-4", ok, f"head speed max error={head_speed_error:.3e} m/s"))

        sample_times = [0, 60, 120, 180, 240, 300]
        sample_handles = [0, 1, 51, 101, 151, 201, 223]
        subset = df[df["time_s"].isin(sample_times) & df["handle_id"].isin(sample_handles)]
        ok = len(subset) == len(sample_times) * len(sample_handles)
        checks.append(("V-KIN-5", ok, f"selected rows={len(subset)} expected={len(sample_times) * len(sample_handles)}"))

        recompute_error = 0.0
        for time_s in sample_times:
            theta = model.solve_head_theta(float(time_s), cfg)
            points, velocities = model.handle_states(theta, cfg)
            actual = df[df["time_s"] == time_s].sort_values("handle_id")
            recomputed = np.column_stack((points, velocities))
            persisted = actual[["x_m", "y_m", "vx_mps", "vy_mps"]].to_numpy(float)
            recompute_error = max(recompute_error, float(np.max(np.abs(recomputed - persisted))))
        ok = recompute_error < 5e-10
        checks.append(("V-KIN-6", ok, f"recomputed sample max error={recompute_error:.3e}"))
    except Exception as exc:  # verification must report a structured failure
        checks.append(("V-KIN-EXCEPTION", False, repr(exc)))

    all_pass = all(item[1] for item in checks)
    print("========== VERIFICATION REPORT ==========")
    print("Stage  : model_1_verify")
    print(f"Result : {'PASS' if all_pass else 'FAIL'}")
    print("Checks :")
    for check_id, passed, detail in checks:
        print(f"  [{check_id}] {'PASS' if passed else 'FAIL'}  {detail}")
    print("==========================================")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
