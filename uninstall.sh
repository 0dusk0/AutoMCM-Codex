#!/usr/bin/env bash
# Remove AutoMCM-Pro skills from OpenAI Codex.

set -euo pipefail

CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"
CODEX_SKILLS_DIR="${CODEX_HOME_DIR}/skills"
SKILLS=("auto-mcm" "cumcm-master" "mcm-master" "draw-image")

echo "AutoMCM-Pro Codex Skill 卸载程序"
echo "目标目录：${CODEX_SKILLS_DIR}"
read -r -p "确认移除 AutoMCM-Pro 的 4 个 Skill？[y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "已取消"
    exit 0
fi

removed=0
for skill in "${SKILLS[@]}"; do
    target="${CODEX_SKILLS_DIR}/${skill}"
    if [[ ! -e "$target" && ! -L "$target" ]]; then
        continue
    fi

    if [[ -f "${target}/SKILL.md" ]] && grep -qi "AutoMCM" "${target}/SKILL.md"; then
        if [[ -L "$target" ]]; then
            rm "$target"
        else
            rm -rf "$target"
        fi
        echo "  ✓ 已移除 \$${skill}"
        removed=$((removed + 1))
    else
        echo "  ⚠ 跳过 \$${skill}：同名 Skill 不是 AutoMCM-Pro"
    fi
done

echo "完成：移除 ${removed} 个 AutoMCM-Pro Skill。"
