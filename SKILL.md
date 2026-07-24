---
name: hermes-doctor
description: "Hermes Agent自诊断与安全自愈插件。用于Agent体检、药方匹配、修复计划、病历记录、凭证完整性检查。当需要检查Agent健康状态、运行自诊断、修复配置问题时使用。"
license: MIT
metadata:
  author: AtomCollide-智械工坊团队
  version: 1.2.0
triggers:
  - 智能体健康
  - Agent诊断
  - 自诊断自愈
  - hermes-doctor
  - 白龙马医生
---

# Hermes Doctor

## Sandbox Runtime Context（v1.2.0）

## 快速开始

```bash
python3 scripts/cli.py --help
python3 scripts/hermes_doctor.py --help
```


新增 `diagnostics/agent_sandbox_runtime_context.py`：生成脱敏的 Agent 沙盒运行环境摘要，暴露 profile、workspace、toolsets、写入边界和非阻断/阻断诊断，用于修复前先拿到上下文。

> 📖 详细文档见 `references/` 目录

Hermes Doctor 是基于 Hermes 自身插件框架重构的 Agent 医生。功能目标对齐皮皮虾医生 PRD，但实现形态属于 Hermes：`.hermes-skill` 插件 manifest、主 `SKILL.md`、子 `skills/`、`agents/`、本地 CLI 和 references 文档。

## When To Use

激活此插件的场景：

- 用户说 `Hermes Doctor 体检`、`看看状态`、`自诊断`
- 用户贴 Hermes 报错、日志、工具调用失败、配置失败、依赖失败
- 用户说 `帮我修一下`、`自愈`、`怎么修`
- 用户需要查询或写入历史处理记录
- 用户要把飞书消息路由到本地 Hermes Doctor 动作
- **凭证完整性检查**（NEW）

不激活的场景：

- 普通聊天或泛化技术科普
- 用户要修的是 皮皮虾医生本体
- 需要绕过登录、验证码、反爬或限流保护

## 核心能力

- **Agent体检**：插件结构/运行线索/日志/工具的只读检查
- **药方匹配**：错误文本→药方库自动匹配
- **修复计划**：生成修复计划（不自动执行）
- **病历记录**：脱敏病历写入与查询
- **凭证完整性**：检测硬编码凭证/格式验证/占位符检测
- **飞书路由**：飞书消息→本地诊断动作

## Core Loop

1. Inspect: 只读收集证据。
2. Triage: 判断严重度、影响范围和风险。
3. Prescribe: 匹配药方。
4. Confirm: 写入、安装、授权、重启、删除前确认。
5. Verify: 运行最小验证。
6. Record: 写入脱敏病历。

## Commands

```bash
python3 scripts/hermes_doctor.py check --target . --format markdown
python3 scripts/hermes_doctor.py match --text "Hermes fetch failed timeout"
python3 scripts/hermes_doctor.py plan --text "unknown tool 工具调用失败"
python3 scripts/hermes_doctor.py record --title "fetch failed" --status partial --summary "what happened"
python3 scripts/hermes_doctor.py search --query "fetch"
python3 scripts/hermes_doctor.py route --text "Hermes Doctor 帮我修一下：fetch failed" --format json
python3 scripts/hermes_doctor.py validate --target .
python3 scripts/hermes_doctor.py test --target .
```

## Subskills

| 子 Skill | 功能 |
|-|-|
| `hermes-check` | 只读体检 Hermes 插件结构、运行线索、日志和工具 |
| `prescription-match` | 把错误文本映射到药方库 |
| `repair-plan` | 生成修复计划，不执行修复 |
| `case-record` | 写入脱敏病历 |
| `case-search` | 查询历史病历 |
| `feishu-route` | 把飞书/Lark 文本路由成本地动作 |

## Credential Integrity Check (NEW)


```python
from modules.credential_integrity import CredentialIntegrityChecker

checker = CredentialIntegrityChecker()

# 检查Agent凭证
results = checker.check_agent_credentials("/path/to/agent")

# 检查环境变量凭证
results = checker.check_environment_credentials()

# 检查技能凭证
results = checker.check_skill_credentials("/path/to/skill")

# 生成报告
report = checker.generate_report(results)
print(f"风险等级: {report['risk_level']}")
```

**检测规则**:
- 硬编码凭证检测
- 凭证格式验证
- 凭证长度检查
- 占位符检测

## Safety

- `.env` 只能检测存在，不能读取或回显内容。
- 不收集 cookie、token、password、private key、session storage。
- 不绕过登录、验证码、反爬或限流。
- 删除、覆盖、reset、读取秘密信息属于 L3，默认只给人工计划。

## 工作流

使用此技能时，按以下步骤执行：
- [ ] 1. 确认用户需求和使用场景
- [ ] 2. 加载相关代码和配置
- [ ] 3. 执行核心功能
- [ ] 4. 验证输出结果
- [ ] 5. 反馈给用户

## 2026-07-03 运行时增强

- 新增诊断事件 session/trace 连续性探针，定位医生链路中的上下文丢失点。
- 验证：新增模块通过 py_compile 和定向 pytest，代码不依赖外部服务。

## 2026-07-03 产品收敛门禁

- 新增 `scripts/product_convergence_gate.py`：从远端干净 clone 后可运行 `python3 scripts/product_convergence_gate.py --json`，检查 SKILL/README、入口文件、smoke 目标、测试与外部融合引用是否自洽。
- 新增 `tests/test_product_convergence_gate.py`：确保门禁在产品仓库中真实可执行，避免后续增强只停留在孤岛模块。

## 一键开箱交付

本仓库提供标准一键入口：

- `install.sh`：用户的一条命令安装与冒烟入口。
- `scripts/setup.py`：安装声明依赖并串联 doctor。
- `scripts/hermes_doctor.py`：统一 CLI（check/match/plan/record/search/route/validate/test）。
- `scripts/doctor.py`：开箱 readiness 门禁（README/SKILL/入口脚本/package scripts 收敛检查）。
- `scripts/smoke.py`：运行 doctor、产品收敛门禁与 Python 编译级冒烟。
- `tests/test_one_click_open_box.py`：契约测试，防止 README 写了但脚本缺失。


## Lark Coding Agent Bridge 融合增强

- 白龙马医生新增 Bridge Preflight Doctor：agent binary、workspace、profile-local lark-cli 三层诊断。
- 新增模块：`diagnostics/agent_bridge_preflight.py`
- 来源模式：飞书/Lark 消息入口、本地 Claude/Codex 执行、会话 fingerprint、profile 隔离与安全门禁。

## Generic orchestration diagnostics

Adds checks for transition-table drift, stale pending events, repeated delivery, missing flow logs, and broken confirmation payloads.
