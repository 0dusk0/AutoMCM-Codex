"""Checks for the pitch sensitivity analysis."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "output" / "sensitivity_pitch.csv"
AUDIT_PATH = ROOT / "output" / "diagnostics" / "sensitivity_audit.json"
FIGURE_PATH = ROOT / "latex" / "images" / "fig_sensitivity_pitch.png"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        df = pd.read_csv(CSV_PATH)
        expected_factors = np.array([0.8, 0.9, 1.0, 1.1, 1.2])
        factors = df["pitch_factor"].to_numpy(float)
        checks.append(("V-SEN-1", np.array_equal(factors, expected_factors), f"factors={factors.tolist()}"))

        numeric = df.select_dtypes(include=[np.number]).to_numpy(float)
        checks.append(("V-SEN-2", bool(np.isfinite(numeric).all()), "all sensitivity values finite"))

        residual = float(df["max_spacing_residual_m"].max())
        checks.append(("V-SEN-3", residual < 1e-8, f"max spacing residual={residual:.3e} m"))

        tail_radius = df["tail_radius_at_300s_m"].to_numpy(float)
        checks.append(("V-SEN-4", bool(np.all(np.diff(tail_radius) > 0)), "tail radius increases with pitch in tested range"))

        base = df.loc[np.isclose(df["pitch_factor"], 1.0)].iloc[0]
        checks.append(("V-SEN-5", abs(float(base["tail_speed_at_300s_mps"]) - 0.9964775397663793) < 1e-8, "base tail speed agrees with model-1 audit"))
        checks.append(("V-SEN-6", FIGURE_PATH.exists() and AUDIT_PATH.exists(), "figure and JSON audit exist"))
    except Exception as exc:
        checks.append(("V-SEN-EXCEPTION", False, repr(exc)))

    all_pass = all(item[1] for item in checks)
    print("========== VERIFICATION REPORT ==========")
    print("Stage  : sensitivity_analysis")
    print(f"Result : {'PASS' if all_pass else 'FAIL'}")
    print("Checks :")
    for check_id, passed, detail in checks:
        print(f"  [{check_id}] {'PASS' if passed else 'FAIL'}  {detail}")
    print("==========================================")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
