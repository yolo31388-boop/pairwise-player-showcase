"""
玩家展示系统 - 验收测试

运行方式：python -m pytest tests/test_player_showcase.py -q
共 12 个测试用例
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.player_showcase import PlayerShowcase


class TestPlayerShowcase:
    """玩家展示系统测试套件"""

    def setup_method(self):
        """每个测试前的初始化"""
        self.system = PlayerShowcase()
        self.system.register_player(
            "p1", level=25, rank="diamond", wins=60, losses=40,
            favorite_weapon="ak47",
            achievements=["first_blood", "mvp"],
            badges=["beta_tester"],
        )

    def test_case_01(self):
        """玩家卡片显示完整信息：ID、等级、段位、胜率、常用武器"""
        card = self.system.player_card("p1")
        assert card["player_id"] == "p1"
        assert card["level"] == 25
        assert card["rank"] == "diamond"
        assert card["win_rate"] == pytest.approx(0.6)
        assert card["favorite_weapon"] == "ak47"

    def test_case_02(self):
        """玩家卡片等级与实际等级一致，不写死"""
        self.system.register_player("p2", level=3)
        self.system.register_player("p3", level=87)
        assert self.system.player_card("p2")["level"] == 3
        assert self.system.player_card("p3")["level"] == 87
        assert self.system.player_card("p2")["level"] != self.system.player_card("p3")["level"]

    def test_case_03(self):
        """玩家卡片支持自定义，不同玩家卡片可以不同"""
        self.system.register_player("p2")
        self.system.customize_card("p1", theme="dark", frame="gold", background="nebula")
        card1 = self.system.player_card("p1")
        card2 = self.system.player_card("p2")
        assert card1["style"] == {"theme": "dark", "frame": "gold", "background": "nebula"}
        assert card2["style"]["theme"] == "default"
        assert card1["style"] != card2["style"]

    def test_case_04(self):
        """名片支持多种背景且可更换（需先解锁）"""
        card = self.system.name_card("p1")
        assert card["background"] == "default"
        with pytest.raises(ValueError):
            self.system.name_card("p1", background="ocean")  # 未解锁不能换
        self.system.unlock_background("p1", "ocean")
        card = self.system.name_card("p1", background="ocean")
        assert card["background"] == "ocean"

    def test_case_05(self):
        """名片背景有稀有度系统"""
        self.system.unlock_background("p1", "galaxy")
        common_card = self.system.name_card("p1", background="default")
        legendary_card = self.system.name_card("p1", background="galaxy")
        assert common_card["background_rarity"] == "common"
        assert legendary_card["background_rarity"] == "legendary"

    def test_case_06(self):
        """名片显示玩家的成就和徽章"""
        card = self.system.name_card("p1")
        assert card["achievements"] == ["first_blood", "mvp"]
        assert card["badges"] == ["beta_tester"]

    def test_case_07(self):
        """展示动作支持多种且可更换"""
        result1 = self.system.emote_action("p1", emote="dance")
        assert result1["emote"] == "dance"
        self.system.update(10.0)  # 跳过冷却
        result2 = self.system.emote_action("p1", emote="salute")
        assert result2["emote"] == "salute"
        with pytest.raises(ValueError):
            self.system.emote_action("p1", emote="not_an_emote")

    def test_case_08(self):
        """展示动作有冷却，冷却内不能反复播放"""
        self.system.emote_action("p1", emote="wave")
        with pytest.raises(ValueError):
            self.system.emote_action("p1", emote="wave")  # 冷却中
        self.system.update(5.0)  # 默认冷却 5 秒
        result = self.system.emote_action("p1", emote="wave")
        assert result["emote"] == "wave"

    def test_case_09(self):
        """展示动作限制场景，比赛中禁止播放"""
        with pytest.raises(ValueError):
            self.system.emote_action("p1", emote="dance", scene="match")
        with pytest.raises(ValueError):
            self.system.emote_action("p1", emote="dance", scene="ranked")
        result = self.system.emote_action("p1", emote="dance", scene="lobby")
        assert result["scene"] == "lobby"

    def test_case_10(self):
        """喷漆有持续时间不会立刻消失，且有数量限制"""
        spray = self.system.spray_paint("p1", (0.0, 0.0), surface="wall")
        assert spray["remaining"] > 1.0  # 不再是写死的 0.1 秒
        self.system.update(0.1)
        assert len(self.system.get_sprays("p1")) == 1  # 0.1 秒后仍存在
        self.system.spray_paint("p1", (10.0, 0.0), surface="wall")
        self.system.spray_paint("p1", (20.0, 0.0), surface="wall")
        with pytest.raises(ValueError):
            self.system.spray_paint("p1", (30.0, 0.0), surface="wall")  # 超过上限 3 个
        self.system.update(30.0)  # 超过持续时间后消失
        assert self.system.get_sprays("p1") == []

    def test_case_11(self):
        """喷漆同位置覆盖旧喷漆，且不能喷在空气等非法表面"""
        self.system.spray_paint("p1", (5.0, 5.0), surface="wall", pattern="a")
        self.system.spray_paint("p1", (5.2, 5.0), surface="wall", pattern="b")  # 同位置覆盖
        sprays = self.system.get_sprays("p1")
        assert len(sprays) == 1
        assert sprays[0]["pattern"] == "b"
        with pytest.raises(ValueError):
            self.system.spray_paint("p1", (0.0, 0.0), surface="air")  # 空气中不能喷

    def test_case_12(self):
        """头衔支持多种、有稀有度和获取条件、位置可调、同时只装备一个"""
        # 默认头衔无条件可用，带稀有度
        badge = self.system.title_badge("p1", title="rookie")
        assert badge["title"] == "rookie"
        assert badge["rarity"] == "common"
        # 获取条件：等级不足不能装备
        with pytest.raises(ValueError):
            self.system.title_badge("p1", title="legend")  # 需要 50 级
        # 满足条件可装备，装备新头衔替换旧头衔（不同时显示多个）
        badge = self.system.title_badge("p1", title="sharpshooter")  # 拥有 first_blood 成就
        assert badge["title"] == "sharpshooter"
        assert badge["rarity"] == "epic"
        badge = self.system.title_badge("p1", title="veteran")  # 25 级 >= 10 级
        assert badge["title"] == "veteran"
        # 显示位置可调整，非法位置报错
        badge = self.system.title_badge("p1", position="bottom")
        assert badge["position"] == "bottom"
        with pytest.raises(ValueError):
            self.system.title_badge("p1", position="middle")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
