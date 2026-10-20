"""Unit tests for Discord Webhook Client."""

import unittest
from unittest.mock import MagicMock, patch
from src.discord_client import DiscordWebhookClient


class TestDiscordClient(unittest.TestCase):
    """Test DiscordWebhookClient URL routing, payload construction, and error recovery."""

    def test_endpoint_url_construction(self):
        """Test URL formatting with and without thread_id and existing query parameters."""
        # Simple URL without thread
        client_no_thread = DiscordWebhookClient("https://discord.com/api/webhooks/123/token")
        self.assertEqual(client_no_thread.endpoint_url, "https://discord.com/api/webhooks/123/token")

        # Simple URL with thread
        client_with_thread = DiscordWebhookClient(
            "https://discord.com/api/webhooks/123/token", thread_id="999888777"
        )
        self.assertEqual(
            client_with_thread.endpoint_url,
            "https://discord.com/api/webhooks/123/token?thread_id=999888777",
        )

        # URL already containing query parameters
        client_with_param = DiscordWebhookClient(
            "https://discord.com/api/webhooks/123/token?wait=true", thread_id="999888777"
        )
        self.assertEqual(
            client_with_param.endpoint_url,
            "https://discord.com/api/webhooks/123/token?wait=true&thread_id=999888777",
        )

    def test_send_message_empty_payload_guard(self):
        """Test that completely empty requests are rejected immediately without network calls."""
        client = DiscordWebhookClient("https://discord.com/api/webhooks/123/token")
        with patch("src.discord_client.requests.post") as mock_post:
            result = client.send_message(content=None, file_items=None)
            self.assertFalse(result)
            mock_post.assert_not_called()

            result_empty_str = client.send_message(content="", file_items=[])
            self.assertFalse(result_empty_str)
            mock_post.assert_not_called()

    @patch("src.discord_client.requests.post")
    def test_send_message_mime_types(self, mock_post):
        """Test that various file extensions map to appropriate MIME types."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = DiscordWebhookClient("https://discord.com/api/webhooks/123/token")
        files = [
            ("pic.png", b"pngdata"),
            ("photo.jpg", b"jpgdata"),
            ("banner.webp", b"webpdata"),
            ("anim.gif", b"gifdata"),
        ]
        result = client.send_message(file_items=files)
        self.assertTrue(result)
        mock_post.assert_called_once()

        posted_files = mock_post.call_args[1]["files"]
        self.assertEqual(posted_files["files[0]"][2], "image/png")
        self.assertEqual(posted_files["files[1]"][2], "image/jpeg")
        self.assertEqual(posted_files["files[2]"][2], "image/webp")
        self.assertEqual(posted_files["files[3]"][2], "image/gif")

    @patch("src.discord_client.time.sleep")
    @patch("src.discord_client.requests.post")
    def test_send_message_429_rate_limit_retry(self, mock_post, mock_sleep):
        """Test automatic backoff and retry when HTTP 429 rate limit is returned."""
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.json.return_value = {"retry_after": 1.5}

        resp_200 = MagicMock()
        resp_200.status_code = 200

        mock_post.side_effect = [resp_429, resp_200]

        client = DiscordWebhookClient("https://discord.com/api/webhooks/123/token")
        result = client.send_message(content="Test message")
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_with(2.0)  # retry_after (1.5) + safety margin (0.5)

    @patch("src.discord_client.time.sleep")
    @patch("src.discord_client.requests.post")
    def test_send_message_413_payload_too_large_bisection(self, mock_post, mock_sleep):
        """Test auto-split bisection when HTTP 413 is encountered and content is preserved."""
        # 1st attempt (batch of 4 items) -> 413
        resp_413 = MagicMock()
        resp_413.status_code = 413

        # Sub-batches (each of 2 items) -> 200 OK
        resp_200 = MagicMock()
        resp_200.status_code = 200

        mock_post.side_effect = [resp_413, resp_200, resp_200]

        client = DiscordWebhookClient("https://discord.com/api/webhooks/123/token")
        file_items = [(f"img_{i}.jpg", b"large_data") for i in range(4)]
        result = client.send_message(content="Header text", file_items=file_items)

        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 3)

        # Check that the first sub-batch preserved the original header content
        call_part1_data = mock_post.call_args_list[1][1]["data"]
        self.assertIn("Header text", call_part1_data["payload_json"])

        # Check that the second sub-batch has no duplicate header content
        call_part2_data = mock_post.call_args_list[2][1]["data"]
        self.assertEqual(call_part2_data, {})


if __name__ == "__main__":
    unittest.main()
