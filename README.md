# pairwise-anim-blend

我们的角色动画在参数超出区间后权重没有归一化，additive 层把根骨骼位移也叠加上去，状态机过渡期间两个 clip 的相位不在同一周期，混合树里 1D 节点在 0.1 和 0.9 之间切换时脚步节奏会突然跳一下；root motion 的 Y 轴被错误地带进水平位移，角色在斜坡上会飘；事件回调在混合时重复触发，同一个 footstep 在一个过渡里播放两次。animation/blend.py 是核心，tests/test_blend.py 15个红。要修的是：按 threshold 归一化权重并处理边界；混合标量和嵌套骨骼轨迹；root motion 只保留水平分量；相位混合要按周期回绕；事件去重保留最新时间；状态机过渡结束后清理旧 clip 的权重。

## 运行

```bash
python -m pytest tests -q
```

初始状态：15 个用例失败。修复实现使全部用例通过，不要修改 `tests/` 下的测试。
