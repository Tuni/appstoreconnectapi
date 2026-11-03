import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "appstoreconnect"))
from api import Api, APIError


class ContentTypeTests(unittest.TestCase):
    def call(self, content_type, payload):
        api = Api.__new__(Api)
        api._debug = False
        api.submit_stats = False
        api._submit_stats = False
        response = Mock(headers={"content-type": content_type}, status_code=200)
        response.json.return_value = payload
        with patch.object(Api, "token", new_callable=PropertyMock, return_value="test"), patch("api.requests.get", return_value=response):
            return api._api_call("https://example.invalid/test")

    def test_json_content_types_with_parameters(self):
        for content_type in ["application/json", "application/json;", "application/json; charset=utf-8", "application/vnd.api+json; charset=utf-8", " Application/JSON ; charset=UTF-8 "]:
            with self.subTest(content_type=content_type):
                self.assertEqual(self.call(content_type, {"data": []}), {"data": []})

    def test_apple_errors_are_not_silently_returned(self):
        with self.assertRaises(APIError):
            self.call("application/json; charset=utf-8", {"errors": [{"detail": "Denied", "status": "403"}]})
