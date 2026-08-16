"""Deterministic input inventory and geometry EDA for CUMCM 2024 A.

This stage has no observational data attachment.  The script therefore audits
the supplied problem assets and visualizes the parameterized initial geometry;
it does not invent measurements or model results.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DIAG_DIR = OUTPUT_DIR / "diagnostics"
IMAGE_DIR = ROOT / "latex" / "images"


PARAMETERS = {
    "contest": "CUMCM 2024 A - Bench Dragon",
    "bench_count": 223,
    "head_bench_count": 1,
    "body_bench_count": 221,
    "tail_bench_count": 1,
    "bench_width_m": 0.30,
    "head_length_m": 3.41,
    "body_tail_length_m": 2.20,
    "hole_diameter_m": 0.055,
    "hole_to_nearest_end_m": 0.275,
    "pitch_problem_1_2_m": 0.55,
    "head_speed_problem_1_mps": 1.0,
    "turning_diameter_m": 9.0,
    "pitch_problem_4_m": 1.70,
}
PARAMETERS["head_handle_spacing_m"] = round(
    PARAMETERS["head_length_m"] - 2 * PARAMETERS["hole_to_nearest_end_m"], 12
)
PARAMETERS["body_handle_spacing_m"] = round(
    PARAMETERS["body_tail_length_m"] - 2 * PARAMETERS["hole_to_nearest_end_m"], 12
)
PARAMETERS["turning_radius_m"] = PARAMETERS["turning_diameter_m"] / 2
PARAMETERS["spiral_a_problem_1_2_m_per_rad"] = (
    PARAMETERS["pitch_problem_1_2_m"] / (2 * np.pi)
)
PARAMETERS["initial_turn_number"] = 16
PARAMETERS["initial_radius_problem_1_2_m"] = (
    PARAMETERS["initial_turn_number"] * PARAMETERS["pitch_problem_1_2_m"]
)


def audit_assets() -> dict:
    data_files = sorted(
        p.name
        for p in DATA_DIR.glob("*")
        if p.is_file() and p.suffix.lower() in {".xlsx", ".xls", ".csv", ".tsv"}
    )
    missing_templates = [
        name
        for name in ("result1.xlsx", "result2.xlsx", "result4.xlsx")
        if not (DATA_DIR / name).exists()
    ]
    checks = {
        "bench_count_consistent": PARAMETERS["bench_count"]
        == PARAMETERS["head_bench_count"]
        + PARAMETERS["body_bench_count"]
        + PARAMETERS["tail_bench_count"],
        "head_handle_spacing_consistent": abs(
            PARAMETERS["head_handle_spacing_m"] - 2.86
        )
        < 1e-12,
        "body_handle_spacing_consistent": abs(
            PARAMETERS["body_handle_spacing_m"] - 1.65
        )
        < 1e-12,
        "no_observation_files": len(data_files) == 0,
    }
    return {
        "data_files": data_files,
        "missing_result_templates": missing_templates,
        "observation_count": 0,
        "missing_value_count": None,
        "outlier_count": None,
        "quality_note": "No measurement/data attachment was supplied; parameters are deterministic problem inputs.",
        "checks": checks,
    }


def save_geometry_figure() -> None:
    a = PARAMETERS["spiral_a_problem_1_2_m_per_rad"]
    theta = np.linspace(0, 32 * np.pi, 5000)
    radius = a * theta
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    r0 = PARAMETERS["initial_radius_problem_1_2_m"]

    fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=180)
    ax.plot(x, y, color="#2b6cb0", linewidth=0.8, label="p = 0.55 m Archimedean spiral")
    ax.scatter([r0], [0], color="#c53030", s=28, zorder=3, label="initial head handle A")
    turn_circle = plt.Circle(
        (0, 0),
        PARAMETERS["turning_radius_m"],
        fill=False,
        linestyle="--",
        color="#d69e2e",
        linewidth=1.0,
        label="turning boundary R = 4.5 m",
    )
    ax.add_patch(turn_circle)
    ax.annotate("A=(8.8, 0)", (r0, 0), xytext=(-42, 14), textcoords="offset points")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Input geometry audit: 16-turn initial spiral")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMAGE_DIR / "fig00_input_geometry.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_assets()
    payload = {"parameters": PARAMETERS, "asset_audit": audit}
    (DIAG_DIR / "input_parameters.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_geometry_figure()
    report_lines = [
        "========== INPUT EDA REPORT ==========",
        f"Contest: {PARAMETERS['contest']}",
        "Observation files: 0 (no data attachment supplied)",
        f"Missing result templates: {', '.join(audit['missing_result_templates'])}",
        f"Bench count check: {'PASS' if audit['checks']['bench_count_consistent'] else 'FAIL'}",
        f"Handle spacing check: {'PASS' if audit['checks']['head_handle_spacing_consistent'] and audit['checks']['body_handle_spacing_consistent'] else 'FAIL'}",
        f"Initial radius check: {PARAMETERS['initial_radius_problem_1_2_m']:.6f} m",
        "Missing/outlier statistics: N/A (no observations)",
        "Figure: latex/images/fig00_input_geometry.png",
        "=======================================",
    ]
    (DIAG_DIR / "data_eda_report.txt").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
