"""Cross-platform console helpers for AutoMCM-Pro CLI scripts."""

from __future__ import annotations

import sys


def configure_utf8_stdio() -> None:
    """Use UTF-8 for CLI output when the active Python streams support it."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            # Embedded or redirected streams may not allow reconfiguration.
            pass
