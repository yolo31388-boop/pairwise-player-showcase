# 玩家展示系统

## 项目描述

玩家展示系统的bug修复项目。核心模块 `ui/player_showcase.py` 存在多个已知bug，需要修复后使测试全部通过。

## 修复内容

- 玩家卡片：显示段位/胜率/常用武器等完整信息，等级取实际值，支持自定义主题/边框/背景
- 名片：多种背景可解锁更换，带稀有度（common/rare/epic/legendary），展示成就与徽章
- 展示动作：多种动作可选，默认 5 秒冷却，比赛/排位场景禁止播放
- 喷漆：默认持续 30 秒，每人最多同时 3 个，同位置自动覆盖，非法表面（如空气）不可喷
- 头衔：多种头衔带稀有度与获取条件（等级/成就），显示位置可调，同时只能装备一个

## 项目结构

```
├── ui/player_showcase.py       # 核心模块（带bug）
├── tests/test_player_showcase.py    # 验收测试（红态）
├── pyproject.toml          # 项目配置
└── README.md               # 说明文档
```

## 运行测试

```bash
python -m pytest tests/test_player_showcase.py -q
```

修复目标：所有 12 个测试全部通过。

## 技术要求

- 纯Python标准库，不引入第三方依赖
- 不修改测试文件
- 保持现有API接口不变
- 修复所有已知bug
