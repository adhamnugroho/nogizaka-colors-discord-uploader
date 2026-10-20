"""Unit tests for configuration module."""

import unittest
from src.config import MEMBERS, validate_config


class TestConfig(unittest.TestCase):
    """Test configuration constants and validators."""

    def test_members_count_and_keys(self):
        """Ensure all 11 Gen 6 members are defined with required attributes."""
        self.assertEqual(len(MEMBERS), 11)
        seen_ids = set()
        for member in MEMBERS:
            self.assertIn("id", member)
            self.assertIn("kanji", member)
            self.assertIn("romaji", member)
            self.assertTrue(member["id"].isdigit())
            self.assertNotIn(member["id"], seen_ids, f"Duplicate member id: {member['id']}")
            seen_ids.add(member["id"])

    def test_official_romaji_corrections(self):
        """Verify official Romaji names that were previously distorted by machine translation."""
        members_by_id = {m["id"]: m for m in MEMBERS}

        # 大越 ひなの -> Hinano Okoshi (not Hino Koshi)
        self.assertEqual(members_by_id["63102"]["romaji"], "Hinano Okoshi")
        self.assertEqual(members_by_id["63102"]["kanji"], "大越 ひなの")

        # 森平 麗心 -> Urumi Morihira (not Raisin Morihira)
        self.assertEqual(members_by_id["63110"]["romaji"], "Urumi Morihira")
        self.assertEqual(members_by_id["63110"]["kanji"], "森平 麗心")

        # 長嶋 凛桜 -> Rio Nagashima (not Nagashima Reno)
        self.assertEqual(members_by_id["63108"]["romaji"], "Rio Nagashima")
        self.assertEqual(members_by_id["63108"]["kanji"], "長嶋 凛桜")

    def test_validate_config(self):
        """Test validate_config with various webhook inputs."""
        # Valid webhook URLs
        self.assertTrue(validate_config("https://discord.com/api/webhooks/123/token"))
        self.assertTrue(validate_config("http://localhost:8080/webhook"))

        # Invalid or empty webhook URLs
        self.assertFalse(validate_config(""))
        self.assertFalse(validate_config("   "))
        self.assertFalse(validate_config("not_a_url"))
        self.assertFalse(validate_config("ftp://discord.com/api/webhooks/123"))

        # Placeholder URLs
        self.assertFalse(validate_config("https://discord.com/api/webhooks/123/your_webhook_token_here"))
        self.assertFalse(validate_config("https://discord.com/api/webhooks/123/your_actual_token"))


if __name__ == "__main__":
    unittest.main()
