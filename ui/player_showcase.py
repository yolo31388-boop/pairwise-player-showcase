"""
玩家展示系统 - 核心模块

功能：
- 玩家卡片：显示完整信息（段位/胜率/常用武器），等级取真实数据，支持自定义外观
- 名片：多种背景、稀有度区分、展示玩家成就与徽章
- 展示动作：多种动作、冷却时间、场景限制（比赛中不可用）
- 喷漆：固定持续时间、每玩家数量上限、同位置覆盖、表面合法性检测
- 头衔徽章：多种头衔、稀有度与解锁条件、显示位置可调、互斥装备
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import time


# 稀有度从低到高
RARITY_ORDER = ["common", "rare", "epic", "legendary"]

# 段位从低到高
RANK_ORDER = [
    "bronze", "silver", "gold", "platinum",
    "diamond", "master", "grandmaster",
]

# 名片背景目录：背景ID -> 稀有度
NAME_CARD_BACKGROUNDS: Dict[str, str] = {
    "default": "common",
    "forest": "common",
    "ocean": "rare",
    "sunset": "rare",
    "galaxy": "epic",
    "inferno": "legendary",
}

# 展示动作目录：动作ID -> 描述
EMOTE_ACTIONS: Dict[str, str] = {
    "wave": "挥手",
    "dance": "跳舞",
    "salute": "敬礼",
    "taunt": "嘲讽",
    "backflip": "后空翻",
}

# 头衔目录：头衔ID -> {稀有度, 解锁条件}
TITLE_CATALOG: Dict[str, Dict[str, Any]] = {
    "rookie": {"rarity": "common", "unlock": {}},
    "veteran": {"rarity": "rare", "unlock": {"matches": 100}},
    "sharpshooter": {"rarity": "epic", "unlock": {"kills": 1000}},
    "champion": {"rarity": "legendary", "unlock": {"rank": "diamond"}},
}

DEFAULT_CONFIG: Dict[str, Any] = {
    # 展示动作
    "emote_cooldown": 5.0,
    "emote_allowed_scenes": ("lobby", "showcase"),
    # 喷漆
    "spray_duration": 30.0,
    "spray_max_per_player": 3,
    "spray_valid_surfaces": ("wall", "ground", "floor", "rock", "crate"),
    # 头衔
    "title_positions": ("top", "bottom", "left", "right"),
}

# 可被空气检测拒绝的“表面”
INVALID_SURFACE = "air"


@dataclass
class Config:
    """配置项"""
    emote_cooldown: float = 5.0
    emote_allowed_scenes: Tuple[str, ...] = ("lobby", "showcase")
    spray_duration: float = 30.0
    spray_max_per_player: int = 3
    spray_valid_surfaces: Tuple[str, ...] = ("wall", "ground", "floor", "rock", "crate")
    title_positions: Tuple[str, ...] = ("top", "bottom", "left", "right")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emote_cooldown": self.emote_cooldown,
            "emote_allowed_scenes": self.emote_allowed_scenes,
            "spray_duration": self.spray_duration,
            "spray_max_per_player": self.spray_max_per_player,
            "spray_valid_surfaces": self.spray_valid_surfaces,
            "title_positions": self.title_positions,
        }


class PlayerShowcase:
    """玩家展示系统核心类"""

    def __init__(self, config: Optional[Dict] = None):
        merged = dict(DEFAULT_CONFIG)
        if config:
            merged.update(config)
        self.config = merged
        self._players: Dict[Any, Dict[str, Any]] = {}
        self._sprays: List[Dict[str, Any]] = []
        self._emote_last: Dict[Any, float] = {}
        self._state: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
        # 内部逻辑时钟，由 update(dt) 推进，保证测试可确定
        self._time = 0.0

    # ------------------------------------------------------------------
    # 通用
    # ------------------------------------------------------------------

    def update(self, dt: float):
        """每帧更新：推进逻辑时钟并清理过期喷漆"""
        if dt < 0:
            raise ValueError("dt 必须非负")
        self._time += dt
        self._sprays = [s for s in self._sprays if s["expires_at"] > self._time]

    def reset(self):
        """重置状态"""
        self._players = {}
        self._sprays = []
        self._emote_last = {}
        self._state = {}
        self._history = []
        self._time = 0.0

    def register_player(
        self,
        player_id: Any,
        level: int = 1,
        rank: str = "bronze",
        wins: int = 0,
        losses: int = 0,
        kills: int = 0,
        matches: Optional[int] = None,
        favorite_weapon: str = "rifle",
        achievements: Optional[List[str]] = None,
        badges: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """注册/更新玩家档案，等级等信息以真实数据为准"""
        if level < 1:
            raise ValueError("等级必须 >= 1")
        if rank not in RANK_ORDER:
            raise ValueError(f"未知段位: {rank}")
        profile = {
            "player_id": player_id,
            "level": int(level),
            "rank": rank,
            "wins": int(wins),
            "losses": int(losses),
            "kills": int(kills),
            "matches": int(matches) if matches is not None else int(wins) + int(losses),
            "favorite_weapon": favorite_weapon,
            "achievements": list(achievements or []),
            "badges": list(badges or []),
            # 展示系统相关状态
            "card_style": {},
            "name_card_background": "default",
            "title": None,
            "title_position": "top",
        }
        self._players[player_id] = profile
        return profile

    def _get_player(self, player_id: Any) -> Dict[str, Any]:
        if player_id not in self._players:
            raise KeyError(f"未注册的玩家: {player_id}")
        return self._players[player_id]

    # ------------------------------------------------------------------
    # 玩家卡片
    # ------------------------------------------------------------------

    def player_card(self, player_id: Any) -> Dict[str, Any]:
        """返回玩家卡片：完整信息 + 真实等级 + 自定义样式"""
        player = self._get_player(player_id)
        total = player["wins"] + player["losses"]
        win_rate = round(player["wins"] / total * 100.0, 1) if total > 0 else 0.0
        return {
            "player_id": player["player_id"],
            "level": player["level"],
            "rank": player["rank"],
            "wins": player["wins"],
            "losses": player["losses"],
            "win_rate": win_rate,
            "kills": player["kills"],
            "matches": player["matches"],
            "favorite_weapon": player["favorite_weapon"],
            "style": dict(player["card_style"]),
        }

    def customize_card(self, player_id: Any, **style: Any) -> Dict[str, Any]:
        """自定义玩家卡片外观（主题、边框、配色等），不同玩家互不影响"""
        player = self._get_player(player_id)
        player["card_style"].update(style)
        return dict(player["card_style"])

    # ------------------------------------------------------------------
    # 名片
    # ------------------------------------------------------------------

    def name_card(self, player_id: Any) -> Dict[str, Any]:
        """返回名片：背景 + 稀有度 + 成就 + 徽章"""
        player = self._get_player(player_id)
        background = player["name_card_background"]
        return {
            "player_id": player["player_id"],
            "background": background,
            "rarity": NAME_CARD_BACKGROUNDS[background],
            "achievements": list(player["achievements"]),
            "badges": list(player["badges"]),
        }

    def set_name_card_background(self, player_id: Any, background: str) -> bool:
        """更换名片背景；背景不存在返回 False"""
        player = self._get_player(player_id)
        if background not in NAME_CARD_BACKGROUNDS:
            return False
        player["name_card_background"] = background
        self._history.append({"type": "name_card_bg", "player": player_id,
                              "background": background, "time": self._time})
        return True

    # ------------------------------------------------------------------
    # 展示动作
    # ------------------------------------------------------------------

    def emote_action(self, player_id: Any, action: str, scene: str = "lobby") -> Optional[Dict[str, Any]]:
        """
        播放展示动作。
        - 动作必须存在
        - 场景必须允许（默认仅大厅/展示界面，比赛中禁用）
        - 受冷却时间限制，冷却中返回 None
        """
        self._get_player(player_id)
        if action not in EMOTE_ACTIONS:
            return None
        if scene not in self.config["emote_allowed_scenes"]:
            return None
        cooldown = float(self.config["emote_cooldown"])
        last = self._emote_last.get(player_id)
        if last is not None and self._time - last < cooldown:
            return None
        self._emote_last[player_id] = self._time
        result = {
            "player_id": player_id,
            "action": action,
            "description": EMOTE_ACTIONS[action],
            "scene": scene,
            "time": self._time,
        }
        self._history.append({"type": "emote", **result})
        return result

    def emote_remaining_cooldown(self, player_id: Any) -> float:
        """剩余冷却时间（秒），无冷却记录时为 0"""
        last = self._emote_last.get(player_id)
        if last is None:
            return 0.0
        remaining = float(self.config["emote_cooldown"]) - (self._time - last)
        return max(0.0, round(remaining, 6))

    # ------------------------------------------------------------------
    # 喷漆
    # ------------------------------------------------------------------

    def spray_paint(
        self,
        player_id: Any,
        position: Tuple[float, float, float],
        surface: str = "wall",
    ) -> Optional[Dict[str, Any]]:
        """
        喷漆：
        - 必须喷在有效表面上（air/空气 拒绝）
        - 持续时间由配置决定（默认30秒），不再是 0.1 秒
        - 同一玩家在同一位置喷漆会覆盖旧喷漆而不是叠加
        - 超过每玩家数量上限时移除最早的喷漆
        """
        self._get_player(player_id)
        valid_surfaces = self.config["spray_valid_surfaces"]
        if surface == INVALID_SURFACE or surface not in valid_surfaces:
            return None
        position = tuple(position)
        duration = float(self.config["spray_duration"])
        if duration <= 0:
            raise ValueError("spray_duration 必须为正数")

        # 同玩家同位置：覆盖刷新，不新增数量
        for spray in self._sprays:
            if spray["player_id"] == player_id and spray["position"] == position:
                spray["surface"] = surface
                spray["created_at"] = self._time
                spray["expires_at"] = self._time + duration
                return dict(spray)

        max_count = int(self.config["spray_max_per_player"])
        mine = [s for s in self._sprays if s["player_id"] == player_id]
        if len(mine) >= max_count:
            oldest = min(mine, key=lambda s: s["created_at"])
            self._sprays.remove(oldest)

        spray = {
            "player_id": player_id,
            "position": position,
            "surface": surface,
            "created_at": self._time,
            "expires_at": self._time + duration,
        }
        self._sprays.append(spray)
        self._history.append({"type": "spray", **dict(spray)})
        return dict(spray)

    def active_sprays(self, player_id: Optional[Any] = None) -> List[Dict[str, Any]]:
        """返回当前仍可见的喷漆（可按玩家过滤）"""
        result = [dict(s) for s in self._sprays if s["expires_at"] > self._time]
        if player_id is not None:
            result = [s for s in result if s["player_id"] == player_id]
        return result

    # ------------------------------------------------------------------
    # 头衔徽章
    # ------------------------------------------------------------------

    def title_unlocked(self, player_id: Any, title: str) -> bool:
        """检查玩家是否满足头衔的获取条件"""
        player = self._get_player(player_id)
        if title not in TITLE_CATALOG:
            return False
        for stat, required in TITLE_CATALOG[title]["unlock"].items():
            if stat == "rank":
                if RANK_ORDER.index(player["rank"]) < RANK_ORDER.index(required):
                    return False
            else:
                if player.get(stat, 0) < required:
                    return False
        return True

    def title_badge(self, player_id: Any) -> Optional[Dict[str, Any]]:
        """返回当前装备的头衔徽章（含稀有度与显示位置），未装备返回 None"""
        player = self._get_player(player_id)
        title = player["title"]
        if title is None:
            return None
        return {
            "player_id": player_id,
            "title": title,
            "rarity": TITLE_CATALOG[title]["rarity"],
            "position": player["title_position"],
        }

    def equip_title(
        self,
        player_id: Any,
        title: str,
        position: Optional[str] = None,
        replace: bool = False,
    ) -> bool:
        """
        装备头衔：
        - 头衔必须存在且满足解锁条件
        - 位置合法（可用 set_title_position 后调）
        - 同一时间只能装备一个头衔：冲突时默认拒绝，replace=True 才替换
        """
        player = self._get_player(player_id)
        if title not in TITLE_CATALOG:
            return False
        if not self.title_unlocked(player_id, title):
            return False
        if position is not None and position not in self.config["title_positions"]:
            return False
        if player["title"] is not None and player["title"] != title and not replace:
            return False
        player["title"] = title
        if position is not None:
            player["title_position"] = position
        self._history.append({"type": "equip_title", "player": player_id,
                              "title": title, "time": self._time})
        return True

    def unequip_title(self, player_id: Any) -> bool:
        """卸下当前头衔"""
        player = self._get_player(player_id)
        if player["title"] is None:
            return False
        player["title"] = None
        return True

    def set_title_position(self, player_id: Any, position: str) -> bool:
        """调整头衔显示位置"""
        player = self._get_player(player_id)
        if position not in self.config["title_positions"]:
            return False
        if player["title"] is None:
            return False
        player["title_position"] = position
        return True
