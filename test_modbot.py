#!/usr/bin/env python
import sys
import logging
import unittest
from unittest import mock
import modbot

# Disable logging
logging.disable(sys.maxsize)


class ModbotTest(unittest.TestCase):
    @mock.patch("modbot.Bot.fetch_reasons")
    @mock.patch("modbot.Reddit")
    def setUp(self, mock_praw, mock_reasons):
        mock_praw.return_value = mock.Mock()
        mock_praw.return_value.subreddit.return_value = mock.Mock()
        mod1 = mock.Mock()
        mod1.name = "foomod"
        mod2 = mock.Mock()
        mod2.name = "barmod"
        mock_praw.return_value.subreddit.return_value.moderator.return_value = iter(
            [mod1, mod2]
        )
        self.bot = modbot.Bot(
            subreddit="Foosub",
            client_id="foo",
            client_secret="bar",
            username="foouser",
            password="foopass",
            webhook="url",
            channel="channel",
        )

        self.bot.reasons = {
            "foo": {"title": "footitle", "id": "fooid", "msg": "foomsg"},
            "bar": {"title": "bartitle", "id": "barid", "msg": "barmsg"},
        }

    def tearDown(self):
        del self.bot

    def test_Bot_init(self):
        self.assertEqual(len(self.bot.mods), 2)
        self.assertEqual(len(self.bot.reasons), 2)
        self.assertIn("foomod", self.bot.mods)
        self.assertIn("barmod", self.bot.mods)
        self.assertIn("foo", self.bot.reasons)
        self.assertIn("bar", self.bot.reasons)
        self.assertEqual(self.bot.subreddit_str, "foosub")
        self.assertEqual(self.bot.webhook, "url")
        self.assertEqual(self.bot.channel, "channel")

    def test_Bot_fetch_reasons(self):
        self.bot.r.get.return_value = {
            "data": {
                "id1": {"title": "Foo", "message": "blah", "id": "id1"},
                "id2": {"title": "Foo Bar", "message": "blah", "id": "id2"},
                "id3": {"title": "Baz/Bar", "message": "blah", "id": "id3"},
            },
            "order": ["id2", "id3", "id1"],
        }
        self.bot.fetch_reasons()
        self.assertEqual(len(self.bot.reasons), 3)
        self.assertIn("foo", self.bot.reasons)
        self.assertIn("foobar", self.bot.reasons)
        self.assertIn("bazbar", self.bot.reasons)

    @mock.patch("modbot.Bot.fetch_reasons")
    def test_Bot_refresh_sub(self, mock_reasons):
        mod3 = mock.Mock()
        mod3.name = "bazmod"
        mod4 = mock.Mock()
        mod4.name = "foobar"
        self.bot.subreddit.moderator.return_value = iter([mod3, mod4])
        self.bot.refresh_sub()
        self.assertEqual(len(self.bot.mods), 2)
        self.assertIn("foobar", self.bot.mods)
        self.assertIn("bazmod", self.bot.mods)
        mock_reasons.assert_called_once()

    @mock.patch("modbot.Bot.handle_report")
    def test_Bot_check_comments_ignore_non_mod(self, mock_handle):
        author = mock.Mock()
        author.name = "user1"
        comment = mock.Mock(banned_by="", author=author)
        self.bot.subreddit.comments.return_value = [comment]
        self.bot.check_comments()
        mock_handle.assert_not_called()

    @mock.patch("modbot.Bot.handle_report")
    def test_Bot_check_comments_by_mod(self, mock_handle):
        author = mock.Mock()
        author.name = "foomod"
        comment = mock.Mock(banned_by="", author=author, body="blah")
        parent = mock.Mock()
        comment.parent.return_value = parent
        self.bot.subreddit.comments.return_value = [comment]
        report = {
            "source": comment,
            "reason": comment.body,
            "author": comment.author.name,
        }
        self.bot.check_comments()
        mock_handle.assert_called_once_with(report, comment.parent())

    def test_check_reports_no_reports(self):
        report = mock.Mock()
        self.bot.report_queue = [report]
        self.bot.subreddit.mod.reports.return_value = []
        self.bot.check_reports()
        self.assertEqual(self.bot.report_queue, [])

    def test_check_reports_skip_reports_in_queue(self):
        report = mock.Mock()
        self.bot.report_queue = [report]
        self.bot.subreddit.mod.reports.return_value = [report]
        self.bot.check_reports()
        self.assertEqual(len(self.bot.report_queue), 1)

    def test_check_reports_mod_report(self)


if __name__ == "__main__":
    unittest.main()
