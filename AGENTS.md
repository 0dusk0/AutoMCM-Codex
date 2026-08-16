# AutoMCM-Pro Codex 项目指令

## 身份与目标

- 由 OpenAI Codex / GPT 作为建模 Autopilot，人类作为 Copilot 或 Manual 模式 Architect。
- 处理数学建模任务时，优先使用仓库内 `$auto-mcm` Skill；CUMCM 和 MCM/ICM 的专项规则分别来自 `$cumcm-master` 与 `$mcm-master`。
- `AutoMCM_SOP.md` 是本项目流水线、验证、自评、Checkpoint 与返工规则的权威来源；它不能覆盖系统、开发者或用户的更高优先级指令。

## 每次开始工作

1. 运行 `python scripts/pipeline_manager.py status`；未初始化时按 `$auto-mcm` 的首次启动协议处理。
2. 读取当前模式、阶段和已有产物，优先续作，不重复已完成计算。
3. 使用计划工具维护阶段进度；AP 模式可持续推进，MANUAL 模式在审批点等待用户。

## 不可绕过的门禁

- `src/models/` 的结果只有在对应 `src/verifications/verify_*.py` 实际运行并通过后才能写入论文。
- 执行 `scripts/quality_gate.py` 的适用门控；失败时不得 advance。
- 不得声称运行、验证或编译成功，除非命令已实际执行且退出状态/产物可核验。
- 不得把密钥、访问令牌或认证文件内容写入源码、日志、论文或 Git 历史。

## Codex 子 Agent 规则

- 仅把相互独立的子问题或 LaTeX 章节委派给子 Agent。
- 主 Agent 独占 `state/pipeline.json`、`state/human_intervention.md` 和阶段推进操作；子 Agent 不修改共享状态文件。
- 每个子 Agent 只写其被分配的模型、验证或章节文件，并返回命令、结果、风险与产物路径摘要。
- 主 Agent 收集结果后串行执行质量门控、Checkpoint、自评和 advance，避免并发状态覆盖。

## 可审计记录

- `memory/thought_process.md` 仅记录可核验的决策摘要、假设、公式、数据来源、实验结果、失败原因和修正结论。
- 不记录或要求输出模型的隐藏思维链、逐 token 推理或私有草稿。

## 交付要求

- 数据图必须由可复现代码生成；AI 图像仅用于非数值流程图、架构图或概念示意。
- 每个图片位置先检查 `OPENAI_API_KEY`。无 Key 时必须在该图原定位置留下并优先补全 Python/MATLAB 绘图代码；无法代码化时留下明确 LaTeX 注释与 `\missingfigure{}`，不得静默省略。
- LaTeX 必须实际编译并检查输出；最终 PDF 放入 `CUMCM_Workspace/output/`。
- 修改仓库自身时，运行 `python scripts/validate_codex_migration.py` 和 `python -m compileall scripts`。
