"""Unit tests for scraper module."""

import unittest
from unittest.mock import MagicMock, patch
from src.scraper import download_image, extract_photo_urls, get_member_photos


class TestScraper(unittest.TestCase):
    """Test HTML parsing and image extraction."""

    def test_extract_photo_urls_filtering(self):
        """Ensure only genuine member gallery photos are extracted while chrome/logos are filtered."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Nogizaka Colors</title></head>
        <body>
            <!-- Logos and navigation icons that MUST be excluded -->
            <img src="/assets/images/logo.png" />
            <img src="/common/icon_twitter.png" />
            <img src="https://www.nogizaka46.com/ogp.jpg" />
            <img src="/images/banner_top.jpg" />
            
            <!-- Authentic member gallery photos under /images/46/ -->
            <img src="/images/46/f9d/photo01.jpg" />
            <img src="https://www.nogizaka46.com/images/46/c5b/photo02.png" />
            <img data-src="/images/46/47e/lazy_photo03.jpg" />
            
            <!-- Duplicate of photo01 -->
            <img src="/images/46/f9d/photo01.jpg" />
        </body>
        </html>
        """
        base_url = "https://www.nogizaka46.com/s/n46/gallery/ngColors_63110"
        urls = extract_photo_urls(sample_html, base_url)

        expected = [
            "https://www.nogizaka46.com/images/46/f9d/photo01.jpg",
            "https://www.nogizaka46.com/images/46/c5b/photo02.png",
            "https://www.nogizaka46.com/images/46/47e/lazy_photo03.jpg",
        ]
        self.assertEqual(urls, expected)

    def test_extract_photo_urls_empty_html(self):
        """Test with empty or tagless HTML."""
        self.assertEqual(extract_photo_urls("", "https://example.com"), [])
        self.assertEqual(extract_photo_urls("<div>Hello world</div>", "https://example.com"), [])

    @patch("src.scraper.requests.get")
    def test_get_member_photos_success(self, mock_get):
        """Test get_member_photos on successful HTTP 200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<img src="/images/46/abc/test.jpg">'
        mock_get.return_value = mock_response

        photos = get_member_photos("63110")
        self.assertEqual(len(photos), 1)
        self.assertIn("/images/46/abc/test.jpg", photos[0])

    @patch("src.scraper.requests.get")
    def test_download_image_success(self, mock_get):
        """Test download_image returning byte content."""
        fake_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_bytes
        mock_get.return_value = mock_response

        data = download_image("https://www.nogizaka46.com/images/46/abc/test.png")
        self.assertEqual(data, fake_bytes)

    @patch("src.scraper.requests.get")
    def test_download_image_failure(self, mock_get):
        """Test download_image returning None on HTTP 404 or connection error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        data = download_image("https://www.nogizaka46.com/images/46/abc/nonexistent.jpg", max_retries=1)
        self.assertIsNone(data)


if __name__ == "__main__":
    unittest.main()
