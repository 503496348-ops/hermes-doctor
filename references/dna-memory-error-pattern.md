# DNA Memory 错误教训融合

> 来源: [DNA Memory](https://github.com/AIPMAndy/dna-memory) — 错误教训与工作流记忆
> 融合目标: 诊断历史错误模式、修复工作流沉淀、跨session错误追踪

## 诊断记忆分型

| 类型 | 诊断应用 |
|------|---------|
| error_lesson | 历史诊断错误（误判/漏判/过度修复） |
| workflow | 验证有效的诊断-修复流程 |
| decision | 诊断策略选择及理由 |
| fact | 已确认的系统状态/配置 |
| insight | 错误模式规律（某类错误常伴随X症状） |
| open_loop | 待根因分析的问题 |

## 错误教训写入规范

```yaml
type: error_lesson
summary: "简述错误及正确做法"
confidence: high
source: session_id
---

# 错误标题

## 症状
用户报告/系统表现

## 错误诊断
初次判断及错误原因

## 正确修复
实际修复步骤

## 预防
如何避免重复
```

## 跨session错误追踪

新诊断开始时：
1. recall相关error_lesson
2. 检查是否为已知模式
3. 匹配则直接应用已验证修复方案
4. 不匹配则作为新模式分析
5. 修复后写入新的error_lesson
