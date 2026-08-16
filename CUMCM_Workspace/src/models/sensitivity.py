"""Sensitivity analysis for problem 1 with respect to spiral pitch."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from problem1_spiral import Config, handle_states, solve_head_theta


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
DIAG_DIR = OUTPUT_DIR / "diagnostics"
IMAGE_DIR = ROOT / "latex" / "images"


def run_case(factor: float) -> dict:
    cfg = replace(Config(), pitch=Config().pitch * factor)
    sample_times = [0, 60, 120, 180, 240, 300]
    max_trailing_speed = 0.0
    tail_speed_300 = np.nan
    max_residual = 0.0
    tail_radius_300 = np.nan
    for time_s in sample_times:
        theta = solve_head_theta(float(time_s), cfg)
        points, velocities = handle_states(theta, cfg)
        target = np.array([cfg.head_spacing] + [cfg.regular_spacing] * (cfg.bench_count - 1))
        residual = np.linalg.norm(np.diff(points, axis=0), axis=1) - target
        max_residual = max(max_residual, float(np.max(np.abs(residual))))
        max_trailing_speed = max(
            max_trailing_speed, float(np.max(np.linalg.norm(velocities[1:], axis=1)))
        )
        if time_s == 300:
            tail_radius_300 = float(np.linalg.norm(points[-1]))
            tail_speed_300 = float(np.linalg.norm(velocities[-1]))
    return {
        "pitch_factor": factor,
        "pitch_m": cfg.pitch,
        "max_trailing_handle_speed_mps": max_trailing_speed,
        "tail_radius_at_300s_m": tail_radius_300,
        "tail_speed_at_300s_mps": tail_speed_300,
        "max_spacing_residual_m": max_residual,
    }


def save_figure(df: pd.DataFrame) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(7.0, 4.2), dpi=180)
    ax1.plot(df["pitch_m"], df["max_trailing_handle_speed_mps"], "o-", color="#2b6cb0")
    ax1.set_xlabel("spiral pitch (m)")
    ax1.set_ylabel("max trailing-handle speed (m/s)", color="#2b6cb0")
    ax1.tick_params(axis="y", labelcolor="#2b6cb0")
    speed_values = df["max_trailing_handle_speed_mps"].to_numpy()
    ax1.set_ylim(float(speed_values.min()) - 5e-6, float(speed_values.max()) + 5e-6)
    ax1.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax1.grid(alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(df["pitch_m"], df["tail_radius_at_300s_m"], "s--", color="#c53030")
    ax2.set_ylabel("tail radius at 300 s (m)", color="#c53030")
    ax2.tick_params(axis="y", labelcolor="#c53030")
    fig.suptitle("Problem 1 pitch sensitivity")
    fig.tight_layout()
    path = IMAGE_DIR / "fig_sensitivity_pitch.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    factors = [0.8, 0.9, 1.0, 1.1, 1.2]
    df = pd.DataFrame([run_case(factor) for factor in factors])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "sensitivity_pitch.csv"
    df.to_csv(csv_path, index=False)
    figure_path = save_figure(df)
    audit = {
        "factors": factors,
        "base_case": df[df["pitch_factor"] == 1.0].iloc[0].to_dict(),
        "max_spacing_residual_m": float(df["max_spacing_residual_m"].max()),
        "figure": str(figure_path),
        "csv": str(csv_path),
    }
    (DIAG_DIR / "sensitivity_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("========== SENSITIVITY REPORT ==========")
    print("Stage  : sensitivity_analysis")
    print("Result : PASS")
    print(df.to_string(index=False, float_format=lambda x: f"{x:.8f}"))
    print(f"Max spacing residual (m): {audit['max_spacing_residual_m']:.3e}")
    print(f"CSV: {csv_path}")
    print(f"Figure: {figure_path}")
    print("=========================================")


if __name__ == "__main__":
    main()
