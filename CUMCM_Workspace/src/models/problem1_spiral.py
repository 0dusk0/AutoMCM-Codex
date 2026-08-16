"""Problem 1: kinematics of the bench dragon on an Archimedean spiral.

All lengths are in metres and angles are in radians.  The fixed distance
between neighbouring handles is an Euclidean chord, because each bench is a
straight rigid board; it is not the arc length of the spiral.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq


ROOT = Path(__file__).resolve().parents[2]
DIAG_DIR = ROOT / "output" / "diagnostics"
OUTPUT_DIR = ROOT / "output"


@dataclass(frozen=True)
class Config:
    pitch: float = 0.55
    head_speed: float = 1.0
    theta_initial: float = 32.0 * np.pi
    duration: int = 300
    bench_count: int = 223
    head_spacing: float = 2.86
    regular_spacing: float = 1.65

    @property
    def a(self) -> float:
        return self.pitch / (2.0 * np.pi)


def gamma(theta: float | np.ndarray, a: float) -> np.ndarray:
    theta_arr = np.asarray(theta, dtype=float)
    r = a * theta_arr
    return np.stack((r * np.cos(theta_arr), r * np.sin(theta_arr)), axis=-1)


def gamma_prime(theta: float | np.ndarray, a: float) -> np.ndarray:
    theta_arr = np.asarray(theta, dtype=float)
    return a * np.stack(
        (
            np.cos(theta_arr) - theta_arr * np.sin(theta_arr),
            np.sin(theta_arr) + theta_arr * np.cos(theta_arr),
        ),
        axis=-1,
    )


def spiral_arc_length(theta: float, a: float) -> float:
    """Arc length from the origin to theta for r=a*theta, theta >= 0."""
    return 0.5 * a * (
        theta * np.sqrt(1.0 + theta * theta) + np.arcsinh(theta)
    )


def solve_head_theta(time_s: float, cfg: Config) -> float:
    target = spiral_arc_length(cfg.theta_initial, cfg.a) - cfg.head_speed * time_s
    if target < 0:
        raise ValueError("Requested time exceeds the available inward spiral arc")
    lo = 0.0
    hi = cfg.theta_initial
    return float(brentq(lambda x: spiral_arc_length(x, cfg.a) - target, lo, hi))


def solve_next_theta(theta_prev: float, spacing: float, a: float) -> float:
    point_prev = gamma(theta_prev, a)

    def residual(theta: float) -> float:
        return float(np.linalg.norm(gamma(theta, a) - point_prev) - spacing)

    lo = theta_prev + 1.0e-10
    hi = theta_prev + max(0.25, spacing / max(a * (theta_prev + 1.0), 1.0))
    while residual(hi) < 0.0:
        hi = theta_prev + 2.0 * (hi - theta_prev)
        if hi - theta_prev > 10.0:
            raise RuntimeError("Could not bracket the next handle on the spiral")
    return float(brentq(residual, lo, hi, xtol=1.0e-12, rtol=1.0e-12))


def handle_angles(head_theta: float, cfg: Config) -> np.ndarray:
    theta = np.empty(cfg.bench_count + 1, dtype=float)
    theta[0] = head_theta
    for j in range(1, len(theta)):
        spacing = cfg.head_spacing if j == 1 else cfg.regular_spacing
        theta[j] = solve_next_theta(theta[j - 1], spacing, cfg.a)
    return theta


def handle_states(head_theta: float, cfg: Config) -> tuple[np.ndarray, np.ndarray]:
    theta = handle_angles(head_theta, cfg)
    theta_prime = gamma_prime(theta, cfg.a)
    points = gamma(theta, cfg.a)
    theta_dot = np.empty_like(theta)
    theta_dot[0] = -cfg.head_speed / np.linalg.norm(theta_prime[0])
    for j in range(1, len(theta)):
        delta = points[j] - points[j - 1]
        denominator = float(np.dot(delta, theta_prime[j]))
        if abs(denominator) < 1.0e-13:
            raise FloatingPointError(f"Degenerate velocity recursion at handle {j}")
        theta_dot[j] = (
            float(np.dot(delta, theta_prime[j - 1])) / denominator * theta_dot[j - 1]
        )
    velocities = theta_prime * theta_dot[:, None]
    return points, velocities


def build_results(cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows: list[dict] = []
    max_spacing_error = 0.0
    min_speed = np.inf
    max_speed = 0.0
    for time_s in range(cfg.duration + 1):
        head_theta = solve_head_theta(time_s, cfg)
        points, velocities = handle_states(head_theta, cfg)
        for j, (point, velocity) in enumerate(zip(points, velocities)):
            label = "龙头前" if j == 0 else "龙尾后" if j == cfg.bench_count else f"把手{j}"
            rows.append(
                {
                    "time_s": time_s,
                    "handle_id": j,
                    "label": label,
                    "x_m": point[0],
                    "y_m": point[1],
                    "vx_mps": velocity[0],
                    "vy_mps": velocity[1],
                    "speed_mps": np.linalg.norm(velocity),
                }
            )
        spacing_errors = np.linalg.norm(np.diff(points, axis=0), axis=1) - np.array(
            [cfg.head_spacing] + [cfg.regular_spacing] * (cfg.bench_count - 1)
        )
        max_spacing_error = max(max_spacing_error, float(np.max(np.abs(spacing_errors))))
        speeds = np.linalg.norm(velocities, axis=1)
        min_speed = min(min_speed, float(np.min(speeds)))
        max_speed = max(max_speed, float(np.max(speeds)))

    long_df = pd.DataFrame(rows)
    sample_times = [0, 60, 120, 180, 240, 300]
    selected = [0, 1, 51, 101, 151, 201, 223]
    sample_df = long_df[
        long_df["time_s"].isin(sample_times) & long_df["handle_id"].isin(selected)
    ].copy()
    audit = {
        "time_rows": cfg.duration + 1,
        "handles_per_time": cfg.bench_count + 1,
        "long_rows": len(long_df),
        "max_handle_spacing_abs_error_m": max_spacing_error,
        "min_handle_speed_mps": min_speed,
        "max_handle_speed_mps": max_speed,
        "head_speed_mps": cfg.head_speed,
    }
    return long_df, sample_df, audit


def write_workbook(long_df: pd.DataFrame, sample_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "result1.xlsx"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        long_df.to_excel(writer, sheet_name="all_handles", index=False)
        sample_df.to_excel(writer, sheet_name="selected_times", index=False)
    return path


def main() -> None:
    cfg = Config()
    long_df, sample_df, audit = build_results(cfg)
    workbook = write_workbook(long_df, sample_df)
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    (DIAG_DIR / "model_1_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("========== MODEL 1 BUILD REPORT ==========")
    print(f"Stage  : model_1_build")
    print(f"Result : PASS")
    print(f"Rows   : {audit['long_rows']} ({audit['time_rows']} times x {audit['handles_per_time']} handles)")
    print(f"Max spacing residual (m): {audit['max_handle_spacing_abs_error_m']:.3e}")
    print(f"Speed range (m/s): [{audit['min_handle_speed_mps']:.6f}, {audit['max_handle_speed_mps']:.6f}]")
    print(f"Workbook: {workbook}")
    print("===========================================")


if __name__ == "__main__":
    main()
