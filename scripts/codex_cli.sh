#!/usr/bin/env bash

# Resolve the Codex CLI across ordinary PATH installs and the Windows Codex app.
# Prints one executable path on success and returns 1 when no CLI is available.
resolve_codex_cli() {
    local candidate=""
    local install_location=""

    if command -v codex >/dev/null 2>&1; then
        candidate="$(command -v codex)"
        # The desktop package also ships a Unix binary named `codex` beside
        # `codex.exe`. Git Bash can see both and may select the Unix binary,
        # which fails on Windows with "Exec format error".
        if [[ "$candidate" == *"/WindowsApps/OpenAI.Codex_"*"/app/resources/codex" ]] \
            && [[ -f "${candidate}.exe" ]]; then
            candidate="${candidate}.exe"
        fi
        printf '%s\n' "$candidate"
        return 0
    fi

    # Git Bash does not always inherit the WindowsApps package path. Ask
    # PowerShell for the installed Codex app location, then convert it to a
    # POSIX path before invoking it from Bash.
    if command -v powershell.exe >/dev/null 2>&1; then
        install_location="$(powershell.exe -NoProfile -NonInteractive -Command \
            '$pkg = Get-AppxPackage -Name OpenAI.Codex -ErrorAction SilentlyContinue | Sort-Object Version -Descending | Select-Object -First 1; if ($pkg) { $pkg.InstallLocation }' \
            2>/dev/null | tr -d '\r' | tail -n 1)"

        if [[ -n "$install_location" ]]; then
            candidate="${install_location}\\app\\resources\\codex.exe"
            if command -v cygpath >/dev/null 2>&1; then
                candidate="$(cygpath -u "$candidate")"
            fi
            if [[ -f "$candidate" ]]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    fi

    return 1
}
