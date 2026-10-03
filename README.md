# 玩家展示系统

## 项目描述

玩家展示系统的bug修复项目。核心模块 `ui/player_showcase.py` 存在多个已知bug，需要修复后使测试全部通过。

## 已知问题

- 玩家卡片信息不全等级写死
- 名片背景只有默认一种无稀有度
- 展示动作只有一个无冷却无场景限制
- 喷漆持续时间太短无数量限制
- 头衔只有默认一种无稀有度无获取条件

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
