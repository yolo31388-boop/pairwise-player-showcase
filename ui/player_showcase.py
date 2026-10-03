"""
玩家展示系统 - 核心模块（修复版）

修复内容：
- 玩家卡片：显示完整信息（段位/胜率/常用武器），等级取实际值，支持自定义样式
- 名片：多种背景可解锁更换，带稀有度，展示成就与徽章
- 展示动作：多种动作，带冷却时间，限制可播放场景
- 喷漆：合理持续时间、数量限制、同位置覆盖、表面合法性校验
- 头衔：多种头衔，带稀有度与获取条件，显示位置可调，同时只能装备一个
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import time


# 稀有度等级，数值越大越稀有
RARITY_ORDER = {"common": 0, "rare": 1, "epic": 2, "legendary": 3}

# 名片背景目录：背景名 -> 稀有度
NAME_CARD_BACKGROUNDS = {
    "default": "common",
    "forest": "common",
    "ocean": "rare",
    "lava": "epic",
    "galaxy": "legendary",
}

# 展示动作目录
EMOTES = ("wave", "dance", "salute", "victory_pose")

# 允许播放展示动作的场景（比赛/排位中禁止，避免影响平衡）
EMOTE_ALLOWED_SCENES = ("lobby", "showcase", "victory")

# 可喷漆表面
VALID_SPRAY_SURFACES = ("wall", "ground", "floor", "ceiling", "object")

# 头衔目录：头衔名 -> 稀有度 + 获取条件
# 条件类型：{"level": n} 等级达到 n；{"achievement": name} 拥有指定成就；None 无条件
TITLE_CATALOG = {
    "rookie": {"rarity": "common", "requirement": None},
    "veteran": {"rarity": "rare", "requirement": {"level": 10}},
    "sharpshooter": {"rarity": "epic", "requirement": {"achievement": "first_blood"}},
    "legend": {"rarity": "legendary", "requirement": {"level": 50}},
}

# 头衔可调整的显示位置
TITLE_POSITIONS = ("top", "bottom", "left", "right")

DEFAULT_SPRAY_DURATION = 30.0   # 喷漆默认持续 30 秒（修复原来写死 0.1 秒的问题）
DEFAULT_SPRAY_LIMIT = 3         # 每个玩家同时存在的喷漆上限
DEFAULT_EMOTE_COOLDOWN = 5.0    # 展示动作默认冷却 5 秒
SPRAY_OVERWRITE_DISTANCE = 1.0  # 距离小于该值视为同一位置，新喷漆覆盖旧喷漆


@dataclass
class Config:
    """配置项"""
    spray_duration: float = DEFAULT_SPRAY_DURATION
    spray_limit: int = DEFAULT_SPRAY_LIMIT
    emote_cooldown: float = DEFAULT_EMOTE_COOLDOWN


class PlayerShowcase:
    """玩家展示系统核心类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._cfg = Config(
            spray_duration=self.config.get("spray_duration", DEFAULT_SPRAY_DURATION),
            spray_limit=self.config.get("spray_limit", DEFAULT_SPRAY_LIMIT),
            emote_cooldown=self.config.get("emote_cooldown", DEFAULT_EMOTE_COOLDOWN),
        )
        self._state = {}
        self._history = []
        self._players: Dict[str, Dict] = {}
        self._now = 0.0  # 内部时钟，由 update(dt) 推进

    # ------------------------------------------------------------------
    # 基础
    # ------------------------------------------------------------------
    def update(self, dt: float):
        """每帧更新：推进时钟，清理过期喷漆"""
        if dt < 0:
            raise ValueError("dt 不能为负数")
        self._now += dt
        for player in self._players.values():
            for spray in player["sprays"]:
                spray["remaining"] -= dt
            player["sprays"] = [s for s in player["sprays"] if s["remaining"] > 0]

    def reset(self):
        """重置状态"""
        self._state = {}
        self._history = []
        self._players = {}
        self._now = 0.0

    def register_player(self, player_id: str, level: int = 1, rank: str = "bronze",
                        wins: int = 0, losses: int = 0,
                        favorite_weapon: str = "rifle",
                        achievements: Optional[List[str]] = None,
                        badges: Optional[List[str]] = None) -> Dict:
        """注册玩家档案"""
        if level < 1:
            raise ValueError("等级必须为正整数")
        player = {
            "player_id": player_id,
            "level": level,
            "rank": rank,
            "wins": wins,
            "losses": losses,
            "favorite_weapon": favorite_weapon,
            "achievements": list(achievements or []),
            "badges": list(badges or []),
            "card_style": {"theme": "default", "frame": "default", "background": "default"},
            "unlocked_backgrounds": {"default"},
            "equipped_background": "default",
            "emote_ready_at": 0.0,
            "sprays": [],
            "equipped_title": None,
            "title_position": "top",
        }
        self._players[player_id] = player
        return player

    def _get_player(self, player_id: str) -> Dict:
        if player_id not in self._players:
            raise ValueError(f"未知玩家: {player_id}")
        return self._players[player_id]

    # ------------------------------------------------------------------
    # 玩家卡片
    # ------------------------------------------------------------------
    def player_card(self, player_id: str) -> Dict:
        """玩家卡片：完整信息 + 实际等级 + 自定义样式"""
        player = self._get_player(player_id)
        total_games = player["wins"] + player["losses"]
        win_rate = player["wins"] / total_games if total_games > 0 else 0.0
        return {
            "player_id": player["player_id"],
            "level": player["level"],  # 实际等级，不再写死
            "rank": player["rank"],
            "wins": player["wins"],
            "losses": player["losses"],
            "win_rate": win_rate,
            "favorite_weapon": player["favorite_weapon"],
            "style": dict(player["card_style"]),
        }

    def customize_card(self, player_id: str, theme: Optional[str] = None,
                       frame: Optional[str] = None,
                       background: Optional[str] = None) -> Dict:
        """自定义玩家卡片样式（主题/边框/背景）"""
        player = self._get_player(player_id)
        if theme is not None:
            player["card_style"]["theme"] = theme
        if frame is not None:
            player["card_style"]["frame"] = frame
        if background is not None:
            player["card_style"]["background"] = background
        return dict(player["card_style"])

    # ------------------------------------------------------------------
    # 名片
    # ------------------------------------------------------------------
    def unlock_background(self, player_id: str, background: str) -> None:
        """解锁名片背景"""
        player = self._get_player(player_id)
        if background not in NAME_CARD_BACKGROUNDS:
            raise ValueError(f"未知名片背景: {background}")
        player["unlocked_backgrounds"].add(background)

    def name_card(self, player_id: str, background: Optional[str] = None) -> Dict:
        """名片：可更换背景（需已解锁）、带稀有度、展示成就与徽章"""
        player = self._get_player(player_id)
        if background is not None:
            if background not in NAME_CARD_BACKGROUNDS:
                raise ValueError(f"未知名片背景: {background}")
            if background not in player["unlocked_backgrounds"]:
                raise ValueError(f"名片背景未解锁: {background}")
            player["equipped_background"] = background
        equipped = player["equipped_background"]
        return {
            "player_id": player["player_id"],
            "background": equipped,
            "background_rarity": NAME_CARD_BACKGROUNDS[equipped],
            "achievements": list(player["achievements"]),
            "badges": list(player["badges"]),
        }

    # ------------------------------------------------------------------
    # 展示动作
    # ------------------------------------------------------------------
    def emote_action(self, player_id: str, emote: str = "wave",
                     scene: str = "lobby") -> Dict:
        """展示动作：多种动作、冷却限制、场景限制"""
        player = self._get_player(player_id)
        if emote not in EMOTES:
            raise ValueError(f"未知展示动作: {emote}")
        if scene not in EMOTE_ALLOWED_SCENES:
            raise ValueError(f"当前场景不允许播放展示动作: {scene}")
        if self._now < player["emote_ready_at"]:
            remaining = player["emote_ready_at"] - self._now
            raise ValueError(f"展示动作冷却中，剩余 {remaining:.1f} 秒")
        player["emote_ready_at"] = self._now + self._cfg.emote_cooldown
        self._history.append(("emote", player_id, emote, scene, self._now))
        return {
            "player_id": player_id,
            "emote": emote,
            "scene": scene,
            "cooldown": self._cfg.emote_cooldown,
        }

    # ------------------------------------------------------------------
    # 喷漆
    # ------------------------------------------------------------------
    def spray_paint(self, player_id: str, position: Tuple[float, float],
                    surface: str = "wall", pattern: str = "default") -> Dict:
        """喷漆：表面校验、同位置覆盖、数量限制、有限持续时间"""
        player = self._get_player(player_id)
        if surface not in VALID_SPRAY_SURFACES:
            raise ValueError(f"无法喷在该表面上: {surface}")
        x, y = position
        # 同位置覆盖：移除距离过近的旧喷漆
        player["sprays"] = [
            s for s in player["sprays"]
            if math.hypot(s["position"][0] - x, s["position"][1] - y)
            >= SPRAY_OVERWRITE_DISTANCE
        ]
        if len(player["sprays"]) >= self._cfg.spray_limit:
            raise ValueError(f"喷漆数量已达上限 ({self._cfg.spray_limit})")
        spray = {
            "position": (x, y),
            "surface": surface,
            "pattern": pattern,
            "remaining": self._cfg.spray_duration,
        }
        player["sprays"].append(spray)
        self._history.append(("spray", player_id, (x, y), surface, self._now))
        return dict(spray)

    def get_sprays(self, player_id: str) -> List[Dict]:
        """获取玩家当前仍存在的喷漆"""
        player = self._get_player(player_id)
        return [dict(s) for s in player["sprays"]]

    # ------------------------------------------------------------------
    # 头衔徽章
    # ------------------------------------------------------------------
    def _title_unlocked(self, player: Dict, title: str) -> bool:
        requirement = TITLE_CATALOG[title]["requirement"]
        if requirement is None:
            return True
        if "level" in requirement:
            return player["level"] >= requirement["level"]
        if "achievement" in requirement:
            return requirement["achievement"] in player["achievements"]
        return False

    def title_badge(self, player_id: str, title: Optional[str] = None,
                    position: Optional[str] = None) -> Dict:
        """头衔徽章：多种头衔、稀有度与获取条件、位置可调、同时只装备一个"""
        player = self._get_player(player_id)
        if title is not None:
            if title not in TITLE_CATALOG:
                raise ValueError(f"未知头衔: {title}")
            if not self._title_unlocked(player, title):
                raise ValueError(f"未满足头衔获取条件: {title}")
            # 冲突检测：装备新头衔会替换旧头衔，不会同时显示多个
            player["equipped_title"] = title
        if position is not None:
            if position not in TITLE_POSITIONS:
                raise ValueError(f"非法头衔显示位置: {position}")
            player["title_position"] = position
        equipped = player["equipped_title"]
        return {
            "player_id": player_id,
            "title": equipped,
            "rarity": TITLE_CATALOG[equipped]["rarity"] if equipped else None,
            "position": player["title_position"],
        }
