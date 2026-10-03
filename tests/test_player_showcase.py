"""
玩家展示系统 - 验收测试

运行方式：python -m pytest tests/test_player_showcase.py -q
共 12 个测试用例
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.player_showcase import (
    PlayerShowcase,
    NAME_CARD_BACKGROUNDS,
    EMOTE_ACTIONS,
    TITLE_CATALOG,
)


class TestPlayerShowcase:
    """玩家展示系统测试套件"""

    def setup_method(self):
        """每个测试前的初始化"""
        self.system = PlayerShowcase()
        self.system.register_player(
            "p1", level=42, rank="gold", wins=30, losses=10,
            kills=1500, matches=200, favorite_weapon="ak47",
            achievements=["first_blood", "mvp"],
            badges=["beta_tester"],
        )

    # ---------------- 玩家卡片 ----------------

    def test_case_01(self):
        """玩家卡片显示完整信息：段位、胜率、常用武器等"""
        card = self.system.player_card("p1")
        assert card["player_id"] == "p1"
        assert card["rank"] == "gold"
        assert card["win_rate"] == 75.0
        assert card["wins"] == 30
        assert card["losses"] == 10
        assert card["favorite_weapon"] == "ak47"

    def test_case_02(self):
        """玩家卡片等级与实际等级一致，不是写死的"""
        assert self.system.player_card("p1")["level"] == 42
        self.system.register_player("p2", level=7)
        assert self.system.player_card("p2")["level"] == 7

    def test_case_03(self):
        """玩家卡片支持自定义，且不同玩家互不影响"""
        self.system.customize_card("p1", theme="dark", border="gold")
        self.system.register_player("p2", level=5)
        card1 = self.system.player_card("p1")
        card2 = self.system.player_card("p2")
        assert card1["style"]["theme"] == "dark"
        assert card1["style"]["border"] == "gold"
        assert card2["style"] == {}

    # ---------------- 名片 ----------------

    def test_case_04(self):
        """名片支持多种背景且可更换，非法背景被拒绝"""
        assert len(NAME_CARD_BACKGROUNDS) > 1
        assert self.system.set_name_card_background("p1", "galaxy") is True
        assert self.system.name_card("p1")["background"] == "galaxy"
        assert self.system.set_name_card_background("p1", "not_exist") is False
        assert self.system.name_card("p1")["background"] == "galaxy"

    def test_case_05(self):
        """名片有稀有度系统，且显示玩家的成就和徽章"""
        rarities = set(NAME_CARD_BACKGROUNDS.values())
        assert len(rarities) > 1
        self.system.set_name_card_background("p1", "inferno")
        card = self.system.name_card("p1")
        assert card["rarity"] == "legendary"
        assert card["achievements"] == ["first_blood", "mvp"]
        assert card["badges"] == ["beta_tester"]

    # ---------------- 展示动作 ----------------

    def test_case_06(self):
        """展示动作支持多种且可更换，非法动作被拒绝"""
        assert len(EMOTE_ACTIONS) > 1
        result = self.system.emote_action("p1", "dance")
        assert result is not None and result["action"] == "dance"
        self.system.update(10.0)
        result = self.system.emote_action("p1", "salute")
        assert result is not None and result["action"] == "salute"
        assert self.system.emote_action("p1", "not_exist") is None

    def test_case_07(self):
        """展示动作有冷却时间，冷却结束后才能再次播放"""
        assert self.system.emote_action("p1", "wave") is not None
        assert self.system.emote_action("p1", "wave") is None
        self.system.update(4.0)
        assert self.system.emote_action("p1", "wave") is None
        self.system.update(1.5)
        assert self.system.emote_action("p1", "wave") is not None

    def test_case_08(self):
        """展示动作受场景限制，比赛中不能播放"""
        assert self.system.emote_action("p1", "taunt", scene="match") is None
        assert self.system.emote_action("p1", "taunt", scene="lobby") is not None

    # ---------------- 喷漆 ----------------

    def test_case_09(self):
        """喷漆有持续时间，不会立刻消失，到期后才消失"""
        spray = self.system.spray_paint("p1", (1.0, 2.0, 3.0), surface="wall")
        assert spray is not None
        assert spray["expires_at"] - spray["created_at"] > 0.1
        self.system.update(1.0)
        assert len(self.system.active_sprays("p1")) == 1
        self.system.update(60.0)
        assert len(self.system.active_sprays("p1")) == 0

    def test_case_10(self):
        """喷漆有数量上限，且同位置喷漆会覆盖而不是叠加"""
        for i in range(5):
            assert self.system.spray_paint("p1", (float(i), 0.0, 0.0)) is not None
        assert len(self.system.active_sprays("p1")) == 3
        # 同位置覆盖：数量不增加，也不叠加
        self.system.spray_paint("p1", (4.0, 0.0, 0.0))
        positions = [s["position"] for s in self.system.active_sprays("p1")]
        assert positions.count((4.0, 0.0, 0.0)) == 1
        assert len(self.system.active_sprays("p1")) == 3

    def test_case_11(self):
        """喷漆必须喷在有效表面上，喷在空气中被拒绝"""
        assert self.system.spray_paint("p1", (0.0, 0.0, 0.0), surface="air") is None
        assert self.system.spray_paint("p1", (0.0, 0.0, 0.0), surface="wall") is not None
        assert len(self.system.active_sprays("p1")) == 1

    # ---------------- 头衔徽章 ----------------

    def test_case_12(self):
        """头衔：多种可选、有稀有度和获取条件、位置可调、同时只能装备一个"""
        assert len(TITLE_CATALOG) > 1
        # 未满足解锁条件的头衔不能装备（champion 需要 diamond 段位）
        assert self.system.equip_title("p1", "champion") is False
        # 满足条件的可以装备（sharpshooter 需要 1000 击杀，p1 有 1500）
        assert self.system.equip_title("p1", "sharpshooter") is True
        badge = self.system.title_badge("p1")
        assert badge["title"] == "sharpshooter"
        assert badge["rarity"] == "epic"
        # 冲突检测：已装备时不能直接再装备第二个
        assert self.system.equip_title("p1", "veteran") is False
        assert self.system.equip_title("p1", "veteran", replace=True) is True
        assert self.system.title_badge("p1")["title"] == "veteran"
        # 显示位置可调整，非法位置被拒绝
        assert self.system.set_title_position("p1", "bottom") is True
        assert self.system.title_badge("p1")["position"] == "bottom"
        assert self.system.set_title_position("p1", "nowhere") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
