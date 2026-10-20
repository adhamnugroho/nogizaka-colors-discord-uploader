"""Unit tests for main CLI pipeline."""

import unittest
from unittest.mock import patch
from main import parse_arguments, run_pipeline


class TestCLI(unittest.TestCase):
    """Test argument parsing and pipeline error paths."""

    def test_parse_arguments_defaults(self):
        """Test argument parsing with default arguments."""
        with patch("sys.argv", ["main.py"]):
            args = parse_arguments()
            self.assertFalse(args.dry_run)
            self.assertIsNone(args.member_id)
            self.assertIsNone(args.webhook_url)
            self.assertIsNone(args.thread_id)
            self.assertEqual(args.delay, 2.0)

    def test_parse_arguments_custom(self):
        """Test argument parsing with explicit CLI flags."""
        test_argv = [
            "main.py",
            "--dry-run",
            "--member-id", "63110",
            "--delay", "1.5",
            "--webhook-url", "https://discord.com/api/webhooks/test/url",
            "--thread-id", "123456",
        ]
        with patch("sys.argv", test_argv):
            args = parse_arguments()
            self.assertTrue(args.dry_run)
            self.assertEqual(args.member_id, "63110")
            self.assertEqual(args.delay, 1.5)
            self.assertEqual(args.webhook_url, "https://discord.com/api/webhooks/test/url")
            self.assertEqual(args.thread_id, "123456")

    def test_run_pipeline_unknown_member_id(self):
        """Test that passing an invalid/unknown member ID returns error code 1."""
        test_argv = ["main.py", "--member-id", "99999", "--dry-run"]
        with patch("sys.argv", test_argv):
            exit_code = run_pipeline()
            self.assertEqual(exit_code, 1)

    def test_run_pipeline_unconfigured_webhook(self):
        """Test that running without --dry-run and without webhook returns error code 1."""
        test_argv = ["main.py", "--member-id", "63110"]
        with patch("sys.argv", test_argv), patch("src.config.DISCORD_WEBHOOK_URL", ""):
            exit_code = run_pipeline()
            self.assertEqual(exit_code, 1)

    @patch("main.get_member_photos")
    def test_run_pipeline_dry_run_success(self, mock_photos):
        """Test that dry-run completes with exit code 0 when member exists."""
        mock_photos.return_value = ["https://www.nogizaka46.com/images/46/fake.jpg"]
        test_argv = ["main.py", "--member-id", "63110", "--dry-run"]
        with patch("sys.argv", test_argv):
            exit_code = run_pipeline()
            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
