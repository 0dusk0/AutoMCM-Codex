---
name: auto-mcm
description: >
  Run AutoMCM-Pro with OpenAI Codex / GPT as the modeling agent. Supports AP (Codex-led) and
  Manual (human-spec-led) dual modes with mandatory GitOps checkpoints, forced
  self-verification of all solver code before LaTeX inclusion, and structured
  human cross-validation at each pipeline stage. Use for both CUMCM (Chinese)
  and MCM/ICM (English) competitions.
---

# AutoMCM-Pro: Codex / GPT 工业级双模态数学建模智能体

**本 Skill 的操作准则文件为 `AutoMCM_SOP.md`。所有行为规范以该文件为最终权威。**

---

## 【唤醒协议】每次被调用时必须首先执行

### Step 1 — 检查工作区是否已初始化

```bash
python scripts/pipeline_manager.py status 2>/dev/null
```

- **退出码 0（已初始化）** → 读取当前阶段和状态，跳到 Step 3
- **退出码非 0（未初始化）** → 执行 **Step 2【首次启动协议】**

---

### Step 2 — 首次启动协议（全程自然语言，用户零命令）

**2a. 用自然语言向用户询问最少必要信息；信息不足时等待回复：**

> "请告诉我：① 题目文件的路径（PDF 或文本），② 附件数据文件所在位置（如有），③ 希望用哪种模式？AP 模式（AI 全自动推进，仅在关键节点可干预）或 MANUAL 模式（每步等待你的审批）？默认 AP。"

**2b. 读取题目，自动推断配置：**

```bash
# 提取题目文本
python -c "import pdfplumber; pdf=pdfplumber.open('PROBLEM_PATH'); [print(p.extract_text()) for p in pdf.pages]" 2>/dev/null \
  || python -c "import pypdf; r=pypdf.PdfReader('PROBLEM_PATH'); [print(p.extract_text()) for p in r.pages]"
```

根据题目内容自动推断：
- 竞赛类型（CUMCM / MCM / ICM）
- 子问题数量（N）
- 是否有数据附件

告知用户推断结果，例如：
> "我分析了题目，检测到 **3 个子问题**。将开启 Codex 子 Agent 并行模式，同时启用竞赛版本控制。是否有补充？"

（默认直接执行，用户沉默 = 确认）

**2c. 自动运行所有初始化命令（静默执行，不让用户看到命令行）：**

```bash
python scripts/setup_workspace.py

python scripts/pipeline_manager.py init \
  --mode {AP|MANUAL} \
  --contest {CUMCM|MCM|ICM} \
  --problems {N} \
  --git

# 将题目和数据复制到工作区
cp PROBLEM_PATH CUMCM_Workspace/data/
cp DATA_FILES   CUMCM_Workspace/data/   # 如有
```

**2d. 以自然语言告知用户就绪状态：**

> "✓ 工作区已就绪！配置：**AP 模式** | **3 个 Codex 并行子 Agent** | **版本控制已开启**。
> 现在开始建模，我会在完成每个阶段后向你汇报进展。"

---

### Step 3 — 根据流水线状态决定行动

| 状态 | Codex / GPT 行为 |
|------|-----------|
| `not_started` | 执行 `start-stage`，静默开始工作 |
| `in_progress` | 直接继续该阶段未完成的工作 |
| `pending_review`（MANUAL 模式） | 用自然语言向用户汇报并等待反馈 |
| `rework` | 读取 `human_intervention.md`，针对性重做，无需用户重新输入命令 |
| `approved` | 执行 `advance`，静默推进，告知用户进展 |

**所有 `pipeline_manager.py` 命令均由 Codex / GPT 执行，用户只需使用自然语言交互。**

### Step 4 — 依赖自检（首次启动 & 每次唤醒）

在开始任何 Python 脚本之前，静默检查并安装必要依赖：

```bash
python -c "import pdfplumber, scipy, numpy, matplotlib, pandas, openpyxl" 2>/dev/null \
  || pip install -q pdfplumber scipy numpy matplotlib pandas openpyxl
```

如需 LaTeX 编译：
```bash
which xelatex >/dev/null 2>&1 || echo "[提示] 未检测到 xelatex，建议安装 TeX Live 或使用 Docker"
```

---

## 【Checkpoint 执行模板】

每次需要发起 Review 时，执行以下命令（填入实际内容）：

```bash
python scripts/pipeline_manager.py request-review \
  --stage "problem_analysis" \
  --summary "## 题目理解\n...\n## 建模策略\n...\n## 文献依据\n..." \
  --results "关键数值/验证输出（从代码实际运行结果复制）" \
  --concerns "存在的不确定点或风险" \
  --next "data_preprocessing"
```

**命令执行后，根据模式决定后续行为：**

### AP 模式 — 自评自批，自动推进，自然语言汇报

1. 在 `state/human_intervention.md` 中写入自评：
```
[APPROVED]
Codex / GPT 自评（<stage>）：
- 本阶段完成情况：<一句话总结>
- 关键数值检查：<列举 2-3 个代表性结果>
- 验证状态：<PASS/本阶段无强制验证>
- 进入下一阶段的理由：<简要说明>
```

2. 执行 advance（静默）：
```bash
python scripts/pipeline_manager.py advance <stage>
```

3. **用自然语言向用户汇报本阶段成果，然后直接开始下一阶段，无需等待任何输入。** 汇报格式示例：
> "✓ **数据预处理**完成。发现 243 条记录，清洗后保留 231 条，缺失值用中位数填补。生成了数据分布图 3 张。→ 开始问题一、二、三并行建模。"

### MANUAL 模式 — 自然语言等待人类反馈

完成阶段后，以自然语言向用户展示汇报摘要，然后明确说：
> "请告诉我是否继续，或者提出修改意见。"

等待用户回复（**用户输入自然语言即可**，无需填写任何文件或输入命令）。  
收到确认后自动写入 `[APPROVED]` 并执行 advance；收到修改意见则直接进入 rework。

---

## 【AP 模式流水线】

### Stage: problem_analysis

```bash
python scripts/pipeline_manager.py start-stage problem_analysis
```

**工作内容：**
1. 读取题目文件（若为 PDF 使用 `pdfplumber` 提取）
2. 在 `memory/thought_process.md` 中写入：
   - 问题类型分析（优化/预测/仿真/图论/混合）
   - 每个小问拟用模型及数学理由
   - 文献调研结果（使用当前 Codex 可用的网页搜索/浏览能力，至少 5 篇可靠来源）
   - 数据质量初判（缺失值、异常值、量纲）
3. AP 模式下：若为 MCM/ICM，检测是否需要 Memo（关键词扫描）
4. **发起 Checkpoint ①**

---

### Stage: data_preprocessing

```bash
python scripts/pipeline_manager.py start-stage data_preprocessing
```

**工作内容：**
1. 编写 `CUMCM_Workspace/src/models/00_data_eda.py`
2. 运行，验证输出合理性
3. 图表 → `latex/images/fig00_*.png`
4. **发起 Checkpoint ②**（含数据分布图和清洗统计）

---

### Stage: model_build + model_verify（AP 模式入口决策）

**进入此阶段时，AP 模式必须首先查询是否启用并行：**

```bash
python scripts/pipeline_manager.py suggest-parallel
```

| 返回值 | 含义 | 行动 |
|--------|------|------|
| 非空字符串（退出码 0） | 多子问题，可并行 | → **路径 A：Codex 并行子 Agent** |
| 空（退出码 1） | 单子问题或条件未满足 | → **路径 B：顺序执行** |

---

#### 路径 A — AP Codex 子 Agent 并行（`problem_count > 1`）

**Step 1** — 主 Agent 对每个问题执行文献门控，然后注册并行 build 批次：
```bash
# suggest-parallel 的输出即为阶段列表，例：model_1_build model_2_build model_3_build
python scripts/quality_gate.py lit --stage model_1_build --problem-n 1
# 对其余问题重复 lit 门控，全部通过后再启动
STAGES=$(python scripts/pipeline_manager.py suggest-parallel)
python scripts/pipeline_manager.py parallel-start $STAGES
```

**Step 2** — 在同一轮中把每个子问题的 build 委派给独立 Codex 子 Agent，并发运行：

- 子 Agent 只能写自己负责的 `src/models/problemN_*.py` 和专属输出文件。
- 子 Agent 不得修改 `state/pipeline.json`、`state/human_intervention.md`，不得执行任何 pipeline 状态命令。
- 每个子 Agent 返回实际运行命令、输出文件、关键数值和风险摘要。
- 主 Agent 收集结果后，对每个 build 串行执行 sanity 门控和 `advance model_N_build`。

**AP 子 Agent Prompt 模板：**
```
你是 AutoMCM-Pro AP 模式的 Codex model_{N} build 子 Agent，只负责问题 {N} 的模型实现与运行。

前置检查：
- 读取 CUMCM_Workspace/state/pipeline.json，确认 mode=AP、data_preprocessing=approved
- 读取 AutoMCM_SOP.md 和已批准的数据预处理产物

执行（严格按顺序，禁止跳步）：
1. 编写 CUMCM_Workspace/src/models/problem{N}_{type}.py。
2. 实际运行模型，将完整 stdout/stderr 保存到 CUMCM_Workspace/output/diagnostics/model_{N}_output.txt。
3. 修复错误和明显数值异常，直到模型稳定运行或明确报告阻塞。
4. 不修改任何 state 文件，不执行 start-stage、request-review 或 advance。

完成后返回：[model_{N}] 状态、实际命令、关键数值、产物路径、未解决风险。
```

**Step 3** — 主 Agent 串行验收 build；全部通过后注册 verify 批次，并把每个验证任务委派给独立子 Agent：
```bash
python scripts/quality_gate.py sanity \
  --stage model_1_build \
  --output-file CUMCM_Workspace/output/diagnostics/model_1_output.txt
python scripts/pipeline_manager.py advance model_1_build
# 对其余 build 重复；全部 approved 后：
python scripts/pipeline_manager.py parallel-start \
  model_1_verify model_2_verify model_3_verify
```

验证子 Agent 只写 `src/verifications/verify_problemN_*.py` 和
`output/diagnostics/model_N_verify.txt`，不得修改共享 state。若验证失败，允许它只修复自己负责的模型与验证文件并复验。

**Step 4** — 主 Agent 等待全部 verify 子 Agent 返回，逐问题串行运行门控、Checkpoint、自评与 advance：

```bash
python scripts/quality_gate.py verify \
  --stage model_1_verify \
  --report-file CUMCM_Workspace/output/diagnostics/model_1_verify.txt
# 通过后执行 request-review，按 AP 模式写入自评，再 advance model_1_verify

python scripts/pipeline_manager.py parallel-all-done \
  model_1_verify model_2_verify model_3_verify
# 退出码 0 → 进入 sensitivity_analysis
# 退出码 1 → 查看 parallel-status，针对未完成项重试
```

**Step 5** — 全部通过后推进：
```bash
python scripts/pipeline_manager.py start-stage sensitivity_analysis
```

---

#### 路径 B — 顺序执行（`problem_count = 1`）

**构建阶段：**
```bash
python scripts/pipeline_manager.py start-stage model_1_build
```

1. 编写 `src/models/problem1_{type}.py`
2. 运行直到无报错、输出合理

**验证阶段（立即接续，强制）：**
```bash
python scripts/pipeline_manager.py start-stage model_1_verify
```

3. 编写 `src/verifications/verify_problem1_{type}.py`
   - 按 `AutoMCM_SOP.md § 4.3` 中对应模型类型的验证清单实现
   - 末尾打印结构化 VERIFICATION REPORT
4. 运行验证脚本，检查所有项目 `✓ PASS`
5. 若有 `✗ FAIL`：**必须回到 model build 修复**，不得跳过
6. **发起 Checkpoint ③**（含完整验证报告原文）

---

### Stage: sensitivity_analysis

```bash
python scripts/pipeline_manager.py start-stage sensitivity_analysis
```

1. 编写 `src/models/sensitivity.py`
2. 编写 `src/verifications/verify_sensitivity.py`（数值稳定性检查）
3. **发起 Checkpoint ④**

---

### Stage: latex_draft

```bash
python scripts/pipeline_manager.py start-stage latex_draft
```

**只有在所有 model_n_verify 阶段均为 `approved` 后，方可开始此阶段。**

1. 使用对应模板（CUMCM → `latex_template.tex`，MCM → `mcm_template.tex`）
2. 按论文结构逐章填写，每章三轮自审（见各自 SKILL 的写作规范）
3. 插入图表时，**确认对应图片文件物理存在** `latex/images/*.png`
   - 数据/结果图 → 必须来自已运行的 Python 代码
   - 流程图 / 概念插图 → 使用 `$draw-image` Skill；设置 `OPENAI_API_KEY` 时调用原项目的 Images API 脚本：
     ```bash
     python scripts/draw_image.py \
       --prompt "..." \
       --output "CUMCM_Workspace/latex/images/figXX_name.png" \
       --quality high
     ```
     调用前必须先运行 `python scripts/draw_image.py --check`。无 Key 时改为 `--fallback python` 或 `--fallback matlab` 生成并补全可复现绘图代码；无法代码化时用 `--fallback comment`，把注释和 `\missingfigure{}` 放到该图原定位置。
4. **发起 Checkpoint ⑤**

---

### Stage: final_compile

```bash
python scripts/pipeline_manager.py start-stage final_compile
python scripts/compile_pdf.py
python scripts/pipeline_manager.py advance final_compile
```

---

## 【Manual 模式附加规程】

Manual 模式下，在开始 `model_{n}_build` 之前，读取 `human_intervention.md`，然后**用自然语言**向用户逐条复述建模规格：

> "我将按以下规格实现问题一：目标函数 max T_shield(θ,v)，决策变量 θ∈[0°,360°]、v∈[70,140] m/s，求解器 SLSQP。有遗漏或歧义请告知，否则我将立即开始。"

用户回复自然语言确认即可，无需填写任何文件。Codex / GPT 将确认写入 `human_intervention.md` 并开始编码。

**在 Manual 模式下，严禁以下行为：**
- 将 `human_intervention.md` 未提及的变量加入目标函数
- 因"数值稳定性"等理由更换人类指定的求解器（需先提问）
- 在论文中添加人类规格外的模型或方法

---

## 【Rework 执行规程】

用户用自然语言提出修改意见后（无需任何命令），Codex / GPT 立即：

1. 将反馈摘要写入 `human_intervention.md`，静默执行：
```bash
python scripts/pipeline_manager.py rework <stage> --feedback "反馈摘要"
```
2. 向用户复述理解到的修改要求，确认无歧义
3. **只修改被明确批评的部分**，其余已 `approved` 的内容不得改动
4. 在 `memory/thought_process.md` 中记录修改方案和关键数值变化
5. 重新运行受影响的验证脚本
6. 完成后用自然语言汇报结果，自动进入下一轮 review

---

## 【运行时操作索引】

- **Codex 子 Agent**：严格使用上方 AP 并行模板和根目录 `AGENTS.md`；子 Agent 不写共享 state。
- **竞赛 Git**：初始化时传 `--git`；需要查询、对比或打标签时先运行 `python scripts/pipeline_manager.py contest-git --help`。
- **质量门控**：按上方 build/verify 阶段和 `AutoMCM_SOP.md § 4` 调用 `scripts/quality_gate.py`；任一门控退出码为 1 时禁止 advance。
- **安全检查**：处理用户路径、外部数据或提交前运行 `python scripts/security_check.py all`，并遵守 `AutoMCM_SOP.md § 7`。
- **LaTeX 编译**：使用 `scripts/compile_pdf.py`，失败时最多修复重试 3 轮，仍失败则请求人工介入。
- **图像生成**：仅为非数值插图使用 `$draw-image`；无 API Key 时必须留下并优先补全 Python/MATLAB 绘图代码，无法代码化时在原图位保留注释和 `\\missingfigure{}`，不允许静默省略。

---

## 【绝对禁止（摘要）】

所有规则详见 `AutoMCM_SOP.md § 7`。核心禁令：
- 不得跳过 Checkpoint
- 不得将 `verify_*` 未通过的模型结果写入论文
- Manual 模式下不得自行发散
- 不得覆写已 `approved` 的内容
