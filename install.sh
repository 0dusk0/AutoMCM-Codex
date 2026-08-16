#!/usr/bin/env bash
# Install AutoMCM-Pro skills for OpenAI Codex.
# Usage:
#   bash install.sh          # symlink installation (recommended)
#   bash install.sh --copy   # copy installation
#   bash install.sh --check  # inspect installation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME_DIR="${CODEX_HOME:-${HOME}/.codex}"
CODEX_SKILLS_DIR="${CODEX_HOME_DIR}/skills"
SKILLS=("auto-mcm" "cumcm-master" "mcm-master" "draw-image")
USE_COPY=0
CHECK_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --copy) USE_COPY=1 ;;
        --check) CHECK_ONLY=1 ;;
        *) echo "未知参数: $arg" >&2; exit 2 ;;
    esac
done

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; B='\033[1m'; N='\033[0m'

echo -e "${C}AutoMCM-Pro — OpenAI Codex Skill 安装器${N}"
echo "Codex home : ${CODEX_HOME_DIR}"
echo "Skills dir : ${CODEX_SKILLS_DIR}"
echo ""

check_installation() {
    local all_ok=1
    for skill in "${SKILLS[@]}"; do
        local dst="${CODEX_SKILLS_DIR}/${skill}"
        if [[ -L "$dst" ]]; then
            echo -e "  ${G}✓${N} \$${skill}  符号链接 → $(readlink "$dst")"
        elif [[ -f "${dst}/SKILL.md" ]]; then
            echo -e "  ${G}✓${N} \$${skill}  文件拷贝"
        else
            echo -e "  ${R}✗${N} \$${skill}  未安装"
            all_ok=0
        fi
    done

    if command -v codex >/dev/null 2>&1; then
        echo -e "  ${G}✓${N} codex CLI → $(command -v codex)"
    else
        echo -e "  ${Y}⚠${N} codex CLI 未在 PATH 中；桌面端仍可加载项目内 Skill"
    fi
    return "$((1 - all_ok))"
}

if [[ "$CHECK_ONLY" -eq 1 ]]; then
    check_installation
    exit $?
fi

if [[ ! -d "${SCRIPT_DIR}/.codex/skills" ]]; then
    echo -e "${R}[错误]${N} 未找到 ${SCRIPT_DIR}/.codex/skills；请从仓库根目录运行。" >&2
    exit 1
fi

mkdir -p "$CODEX_SKILLS_DIR"

for skill in "${SKILLS[@]}"; do
    src="${SCRIPT_DIR}/.codex/skills/${skill}"
    dst="${CODEX_SKILLS_DIR}/${skill}"

    if [[ ! -f "${src}/SKILL.md" ]]; then
        echo -e "${R}[错误]${N} 缺少 ${src}/SKILL.md" >&2
        exit 1
    fi

    if [[ -L "$dst" ]]; then
        rm "$dst"
    elif [[ -e "$dst" ]]; then
        if [[ -f "${dst}/SKILL.md" ]] && grep -qi "AutoMCM" "${dst}/SKILL.md"; then
            rm -rf "$dst"
        else
            backup="${dst}.backup.$(date +%Y%m%d%H%M%S)"
            mv "$dst" "$backup"
            echo -e "  ${Y}⚠${N} 已将同名非 AutoMCM Skill 备份到 $backup"
        fi
    fi

    if [[ "$USE_COPY" -eq 1 ]]; then
        cp -R "$src" "$dst"
        echo -e "  ${G}✓${N} 拷贝 \$${skill}"
    else
        ln -s "$src" "$dst"
        echo -e "  ${G}✓${N} 链接 \$${skill}"
    fi
done

echo ""
check_installation
echo ""
echo -e "${G}安装成功。${N}在 Codex 中输入自然语言，或显式调用："
echo -e "  ${C}\$auto-mcm${N}      — AP / MANUAL 双模式入口"
echo -e "  ${C}\$cumcm-master${N}  — 国赛中文论文"
echo -e "  ${C}\$mcm-master${N}    — MCM/ICM 英文论文"
echo ""
echo "启动脚本：bash start_modeling.sh --contest cumcm -p problem.pdf -d ./data"
