---
name: hermes-doctor
description: "Hermes Agent自诊断与安全自愈插件。用于Agent体检、药方匹配、修复计划、病历记录、凭证完整性检查。当需要检查Agent健康状态、运行自诊断、修复配置问题时使用。"
version: 0.3.0
author: AtomCollide-智械工坊团队
tags: [hermes, doctor, diagnosis, self-healing, agent, credential-integrity]
requires_tools: [read_file, write_file, patch, search_files, terminal, clarify]
requires_toolsets: [file, terminal]

triggers:
  - 智能体健康
  - Agent诊断
  - 自诊断自愈
  - hermes-doctor
  - 白龙马医生
---

# Hermes Doctor

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

融合自 langgenius/dify 的凭证完整性验证机制。

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
