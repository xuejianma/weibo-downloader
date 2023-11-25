import unittest
from unittest.mock import patch, MagicMock
from weibo_downloader import WeiboDownloader

class TestWeiboDownloader(unittest.TestCase):

    def test_initialization_with_no_parameters(self):
        """Test initialization without username and uid."""
        with self.assertRaises(ValueError):
            WeiboDownloader()

    def test_initialization_with_both_username_and_uid(self):
        """Test initialization with both username and uid."""
        with self.assertRaises(ValueError):
            WeiboDownloader(username="dummy_user", uid="123456")

    @patch('requests.get')
    def test_get_uid_from_username(self, mock_get):
        """Test fetching UID from username."""
        expected_uid = 123456
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "cards": [
                    {},
                    {"card_group": [{"user": {"id": expected_uid}}]}
                ]
            }
        }
        mock_get.return_value = mock_response

        downloader = WeiboDownloader(username="dummy_user")
        uid = downloader.get_uid_from_username("dummy_user")
        self.assertEqual(uid, expected_uid)

    def test_filter_date_format_valid(self):
        """Test filtering valid date format."""
        downloader = WeiboDownloader(username="dummy_user")
        date = "2023-01-01"
        filtered_date = downloader.filter_date_format(date)
        self.assertEqual(str(filtered_date), date)

    def test_filter_date_format_invalid(self):
        """Test filtering invalid date format."""
        downloader = WeiboDownloader(username="dummy_user")
        with self.assertRaises(ValueError):
            downloader.filter_date_format("invalid-date")
