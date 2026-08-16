#!/usr/bin/env python3
"""
Generate an image through the OpenAI Images API and save it to disk.

Default model: gpt-image-2.
Compatibility models: gpt-image-1.5, gpt-image-1, gpt-image-1-mini.

Authentication:
  OPENAI_API_KEY env var → uses the OpenAI Python SDK directly.

This script deliberately does not infer image capability from a Codex CLI
installation and does not inspect Codex login files. A Codex-native image tool,
when actually exposed by the current runtime, is a separate invocation path.

Exit codes:
  0  Image saved successfully
  1  Runtime error (API failure, bad params, import missing)
  2  API key unavailable — a Python/MATLAB/LaTeX fallback was written

Usage:
  python scripts/draw_image.py --prompt "..." --output "latex/images/fig_flow.png"
  python scripts/draw_image.py --check          # auth check only, no generation
  python scripts/draw_image.py --prompt "..." --output "..." --size 1536x1024 --quality high
  python scripts/draw_image.py --prompt "..." --output "out.jpg" --output-format jpeg --compression 80
  python scripts/draw_image.py --prompt "..." --output "..." --fallback matlab

gpt-image-2 size rules (any WxH string is accepted):
  • Each edge must be a multiple of 16 px
  • Maximum edge ≤ 3840 px
  • Long-to-short edge ratio ≤ 3:1
  • Total pixels: 655,360 – 8,294,400
  Common presets: 1024x1024, 1536x1024, 1024x1536, 2048x2048,
                  2048x1152, 1152x2048, 3840x2160, 2160x3840

Requires (API path):
  pip install openai>=1.0
  export OPENAI_API_KEY=sk-...
  Organization verification at platform.openai.com/settings/organization/general
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from console_utils import configure_utf8_stdio

configure_utf8_stdio()


# Keep the orchestration-model namespace separate from image-model selection.
DEFAULT_IMAGE_MODEL = "gpt-image-2"
SUPPORTED_IMAGE_MODELS = (
    "gpt-image-2",
    "gpt-image-1.5",
    "gpt-image-1",
    "gpt-image-1-mini",
)
DEPRECATED_IMAGE_MODELS = set(SUPPORTED_IMAGE_MODELS) - {DEFAULT_IMAGE_MODEL}
FALLBACK_KINDS = ("python", "matlab", "comment")

# gpt-image-2 does not currently support transparent backgrounds.
_TRANSPARENT_UNSUPPORTED = {"gpt-image-2"}

def check_auth() -> dict:
    """
    Probe available authentication and return a status dict.

    Returns:
        {
            "available": bool,
            "method": "api_key" | "none",
            "key": str | None,   # set only for api_key method
            "message": str,
        }
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        return {
            "available": True,
            "method": "api_key",
            "key": api_key,
            "message": "OPENAI_API_KEY is set — API path available",
        }

    return {
        "available": False,
        "method": "none",
        "key": None,
        "message": (
            "No auth available.  To enable draw-image:\n"
            "  API path :  export OPENAI_API_KEY=sk-proj-...\n"
            "              (get key at https://platform.openai.com/api-keys)\n"
            "  No-key path: run the normal command with --fallback python, matlab,\n"
            "               or comment; python is the default.\n"
            "  Codex-native image generation is separate from this script and may\n"
            "  be used only when the current runtime actually exposes that tool."
        ),
    }


def resolve_image_model(cli_model: str | None) -> str:
    """Resolve only the Images API model; never reuse the Codex agent model."""
    model = cli_model or os.environ.get("AUTOMCM_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL
    if model not in SUPPORTED_IMAGE_MODELS:
        supported = ", ".join(SUPPORTED_IMAGE_MODELS)
        raise ValueError(f"unsupported image model {model!r}; choose one of: {supported}")
    return model


def resolve_fallback_kind(cli_fallback: str | None) -> str:
    """Resolve the mandatory no-key fallback format."""
    kind = cli_fallback or os.environ.get("AUTOMCM_IMAGE_FALLBACK") or "python"
    if kind not in FALLBACK_KINDS:
        supported = ", ".join(FALLBACK_KINDS)
        raise ValueError(f"unsupported fallback {kind!r}; choose one of: {supported}")
    return kind


def _default_fallback_path(output: str, kind: str) -> Path:
    """Place fallback source in the workspace when the standard layout is used."""
    out = Path(output)
    extension = {"python": ".py", "matlab": ".m", "comment": ".tex"}[kind]

    if out.parent.name.lower() == "images" and out.parent.parent.name.lower() == "latex":
        workspace = out.parent.parent.parent
        if kind == "comment":
            return workspace / "latex" / f"{out.stem}_fallback{extension}"
        return workspace / "src" / "figures" / f"{out.stem}{extension}"

    return out.with_name(f"{out.stem}_fallback{extension}")


def write_fallback(
    prompt: str,
    output: str,
    kind: str,
    fallback_output: str | None = None,
) -> Path:
    """Write a non-destructive figure fallback and return its path."""
    path = Path(fallback_output) if fallback_output else _default_fallback_path(output, kind)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        print(f"[draw_image] FALLBACK EXISTS — preserved without overwrite: {path}")
        return path

    if kind == "python":
        content = f'''#!/usr/bin/env python3
"""Fallback figure scaffold generated because OPENAI_API_KEY was unavailable."""

from pathlib import Path

import matplotlib.pyplot as plt


OUTPUT = Path({output!r})
FIGURE_REQUIREMENT = {prompt!r}


def main() -> None:
    """Replace the placeholder layout below with a reproducible implementation."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis("off")
    ax.text(0.5, 0.62, "TODO: implement this figure with matplotlib/networkx",
            ha="center", va="center", fontsize=14, weight="bold")
    ax.text(0.5, 0.42, FIGURE_REQUIREMENT, ha="center", va="center",
            fontsize=10, wrap=True)
    fig.savefig(OUTPUT, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
'''
    elif kind == "matlab":
        matlab_output = output.replace("'", "''")
        prompt_comments = "\n".join(f"% {line}" for line in prompt.splitlines())
        content = f'''% Fallback figure scaffold generated because OPENAI_API_KEY was unavailable.
% Replace the placeholder layout below with a reproducible MATLAB implementation.
% Intended figure requirement:
{prompt_comments}

outputPath = '{matlab_output}';
outputDir = fileparts(outputPath);
if ~isempty(outputDir) && ~exist(outputDir, 'dir')
    mkdir(outputDir);
end

fig = figure('Visible', 'off', 'Color', 'white', 'Position', [100 100 1200 720]);
axis off;
text(0.5, 0.60, 'TODO: implement this figure with MATLAB', ...
    'HorizontalAlignment', 'center', 'FontSize', 16, 'FontWeight', 'bold');
text(0.5, 0.42, 'See source comments for the intended figure requirement.', ...
    'HorizontalAlignment', 'center', 'FontSize', 11);
exportgraphics(fig, outputPath, 'Resolution', 300);
close(fig);
'''
    else:
        prompt_comments = "\n".join(f"% {line}" for line in prompt.splitlines())
        content = f'''% AutoMCM-Pro figure fallback: OPENAI_API_KEY was unavailable.
% Intended output: {output}
% Intended figure requirement:
{prompt_comments}
% TODO: replace this block with \\includegraphics after producing the figure.
\\missingfigure{{Pending figure: {Path(output).name}; see the comments above.}}
'''

    path.write_text(content, encoding="utf-8")
    print(f"[draw_image] FALLBACK WRITTEN ({kind}) → {path.resolve()}")
    return path


def _infer_format(output_path: str, explicit_format: str | None) -> str:
    if explicit_format:
        return explicit_format
    ext = Path(output_path).suffix.lower().lstrip(".")
    return {"jpg": "jpeg"}.get(ext, ext) if ext in ("jpg", "jpeg", "webp") else "png"


def generate(
    prompt: str,
    output: str,
    size: str,
    quality: str,
    model: str,
    output_format: str | None,
    compression: int | None,
    background: str,
    moderation: str,
    fallback: str,
    fallback_output: str | None,
) -> None:
    auth = check_auth()

    if not auth["available"]:
        path = write_fallback(prompt, output, fallback, fallback_output)
        print(f"[draw_image] NO API KEY — use or complete fallback: {path}", file=sys.stderr)
        sys.exit(2)

    # ── API key path ──────────────────────────────────────────────────
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed — run: pip install openai", file=sys.stderr)
        sys.exit(1)

    fmt = _infer_format(output, output_format)

    if model in DEPRECATED_IMAGE_MODELS:
        print(
            f"[draw_image] WARNING: {model} is retained only for compatibility; "
            f"prefer {DEFAULT_IMAGE_MODEL}",
            file=sys.stderr,
        )

    if background == "transparent" and model in _TRANSPARENT_UNSUPPORTED:
        print(
            f"[draw_image] WARNING: {model} does not support transparent backgrounds"
            " — falling back to 'opaque'",
            file=sys.stderr,
        )
        background = "opaque"

    client = OpenAI(api_key=auth["key"])
    print(
        f"[draw_image] model={model}  size={size}  quality={quality}"
        f"  format={fmt}  background={background}"
    )
    print(f"[draw_image] prompt: {prompt}")

    kwargs: dict = dict(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
        quality=quality,
        output_format=fmt,
        background=background,
        moderation=moderation,
    )
    if compression is not None and fmt in ("jpeg", "webp"):
        kwargs["output_compression"] = compression

    response = client.images.generate(**kwargs)

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    img = response.data[0]
    if getattr(img, "b64_json", None):
        out.write_bytes(base64.b64decode(img.b64_json))
    elif getattr(img, "url", None):
        import urllib.request
        urllib.request.urlretrieve(img.url, str(out))
    else:
        print("ERROR: API returned no image data", file=sys.stderr)
        sys.exit(1)

    if hasattr(response, "usage") and response.usage:
        u = response.usage
        print(
            f"[draw_image] tokens — input: {u.input_tokens}"
            f"  output: {u.output_tokens}  total: {u.total_tokens}"
        )

    print(f"[draw_image] SAVED → {out.resolve()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Generate an image via OpenAI gpt-image-2 (or older models)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--check", action="store_true",
                    help="Check auth status only, do not generate an image")
    ap.add_argument("--prompt",
                    help="Image description (max 32,000 chars)")
    ap.add_argument("--output",
                    help="Destination file path (.png / .jpg / .webp)")
    ap.add_argument(
        "--model",
        default=None,
        help=(
            "Images API model. Resolution order: --model, AUTOMCM_IMAGE_MODEL, "
            "gpt-image-2. This is independent of the Codex agent model."
        ),
    )
    ap.add_argument("--size", default="1024x1024",
                    help=(
                        "Image dimensions. gpt-image-2: any WxH where each edge is a multiple "
                        "of 16, max 3840, ratio ≤ 3:1. "
                        "Common: 1024x1024, 1536x1024, 1024x1536, 2048x2048, 3840x2160. "
                        "(default: 1024x1024)"
                    ))
    ap.add_argument("--quality", default="medium",
                    choices=["low", "medium", "high", "auto"],
                    help="Rendering quality (default: medium). Use 'high' for final figures.")
    ap.add_argument("--output-format", dest="output_format", default=None,
                    choices=["png", "jpeg", "webp"],
                    help="Image file format (default: inferred from --output extension, else png)")
    ap.add_argument("--compression", type=int, default=None, metavar="0-100",
                    help="Compression for jpeg/webp (0=max quality, 100=max compression)")
    ap.add_argument("--background", default="opaque",
                    choices=["opaque", "transparent", "auto"],
                    help="Background type. Note: gpt-image-2 does not support transparent.")
    ap.add_argument("--moderation", default="auto",
                    choices=["auto", "low"],
                    help="Content moderation strictness (default: auto)")
    ap.add_argument(
        "--fallback",
        default=None,
        choices=list(FALLBACK_KINDS),
        help=(
            "No-key fallback: python (default), matlab, or comment. "
            "Can also be set with AUTOMCM_IMAGE_FALLBACK."
        ),
    )
    ap.add_argument(
        "--fallback-output",
        default=None,
        help="Optional explicit path for the generated fallback source/snippet.",
    )
    args = ap.parse_args()

    if args.check:
        auth = check_auth()
        print(f"[draw_image:check] method={auth['method']}  available={auth['available']}")
        print(f"[draw_image:check] {auth['message']}")
        sys.exit(0 if auth["available"] else 2)

    if not args.prompt or not args.output:
        ap.error("--prompt and --output are required (or use --check for auth check only)")

    try:
        image_model = resolve_image_model(args.model)
        fallback_kind = resolve_fallback_kind(args.fallback)
    except ValueError as exc:
        ap.error(str(exc))

    generate(
        prompt=args.prompt,
        output=args.output,
        size=args.size,
        quality=args.quality,
        model=image_model,
        output_format=args.output_format,
        compression=args.compression,
        background=args.background,
        moderation=args.moderation,
        fallback=fallback_kind,
        fallback_output=args.fallback_output,
    )
