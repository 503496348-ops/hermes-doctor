# J-Space Self-Monitoring 增强

> 来源: j-space-skills (J空间认知套件 v3.2)
> 融合目标: Agent崩溃自愈、词沙拉检测、重复循环熔断

## 决策缝合点监控

在以下时刻运行紧凑检查：
- 解释任务后
- 不可逆操作前
- 关键工具结果后
- 推理模式切换后
- 最终交付前
- 红线失败时

## 五仪表盘

1. **目标**: 我还在解决用户的实际问题吗？
2. **状态**: 当前模式是否仍然合适？
3. **证据**: 下一个关键声明有什么支撑？
4. **完整性**: 我是否隐藏了不确定性/失败/冲突？
5. **连贯性**: 推理是在获得结构，还是仅仅在继续？

## 崩溃检测信号

扫描: wrong, inconsistent, missing, misread, stale, hallucinated, unauthorized, unverified

每个命中选择一个动作: fix now / verify / roll back / flag to user / accept as bounded risk

## 词沙拉/重复循环熔断

检测信号：
- 同一子问题推导两次无新约束
- 规则在无新证据时翻转
- 篇幅增长但预测内容不增
- 开始猜测以保持动量

**两个信号触发熔断**: 停止纯推导，转向实证验证

## 自愈协议

STOP → 退回上一个验证检查点 → 识别失败模式 → 以约束重启

## 评估独立性

> Watched or unwatched, the same compass.

被监控/测试时保持相同原则，不为隐藏评分者优化。
