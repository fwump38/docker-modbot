#!/usr/bin/venv python

import os
import json
import logging
import re
import sys
import time
import datetime

import requests
from praw import Reddit
from praw.models.reddit.comment import Comment
from praw.models.reddit.submission import Submission

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)

__author__ = "/u/fwump38"
__version__ = "1.0.0"


def clean(obj):
    """Parses out all _Block objects into dicts and removes Nonetypes in order to convert to JSON"""
    logger.debug(f"Cleaning object: {obj}")
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(clean(x) for x in obj if x is not None)
    elif isinstance(obj, dict):
        return type(obj)(
            (clean(k), clean(v))
            for k, v in obj.items()
            if k is not None and v is not None
        )
    elif isinstance(obj, _Block):
        return clean(obj.__dict__)
    else:
        return obj


def display(cleaned):
    """Outputs the JSON string that would be sent to Slack"""
    logger.debug("Making JSON string for Block objects")
    json_dump = json.dumps(cleaned, indent=4)
    return json_dump


class _Block:
    """Base class for use with Slack Block Kit. Allows easy creation of block kit messages with validation of all components."""

    def __init__(self):
        pass

    def check_instance(self, obj, attr, instance):
        logger.debug(
            f"Checking that {obj.__class__.__name__}.{attr} is instance of {instance}"
        )
        obj_value = getattr(obj, attr)
        if not isinstance(obj_value, instance):
            msg = f"{obj.__class__.__name__}.{attr} is instance of {obj_value.__class__.__name__} but should be an instance of {instance}."
            raise TypeError(msg)

    def check_type(self, obj, attr, objtype):
        logger.debug(
            f"Checking that {obj.__class__.__name__}.{attr} is of type {objtype}"
        )
        obj_value = getattr(obj, attr)
        if not type(obj_value) == objtype:
            msg = f"{obj.__class__.__name__}.{attr} is of type {type(obj_value)} but should be of type {objtype}."
            raise TypeError(msg)

    def check_len(self, obj, attr, max_length):
        logger.debug(
            f"Checking that {obj.__class__.__name__}.{attr} length does not exceed {max_length}"
        )
        obj_value = getattr(obj, attr)
        if len(obj_value) > max_length:
            msg = f"{obj.__class__.__name__}.{attr} length is {len(obj_value)} but should not exceed {max_length}."
            raise ValueError(msg)

    def check_equal(self, obj, attr, value):
        logger.debug(
            f"Checking that {obj.__class__.__name__}.{attr} is equal to {value}"
        )
        obj_value = getattr(obj, attr)
        if obj_value != value:
            msg = f"{obj.__class__.__name__}.{attr} is {obj_value} but should equal {value}."
            raise ValueError(msg)

    def check_instance_list(self, obj, attr, instance):
        logger.debug(
            f"Checking that all elements of {obj.__class__.__name__}.{attr} are instance of {instance}"
        )
        obj_value = getattr(obj, attr)
        for c, item in enumerate(obj_value):
            if not isinstance(item, instance):
                msg = f"{obj.__class__.__name__}.{attr} at index {c} is instance of {item.__class__.__name__} but should be an instance of {instance}."
                raise TypeError(msg)

    def check_len_list(self, obj, attr, max_length):
        logger.debug(
            f"Checking that all elements of {obj.__class__.__name__}.{attr} length do not exceed {max_length}"
        )
        obj_value = getattr(obj, attr)
        for c, item in enumerate(obj_value):
            if isinstance(item, _Text):
                if len(item.text) > max_length:
                    msg = f"{obj.__class__.__name__}.{attr} at index {c} length is {len(item.text)} but should not exceed {max_length}."
                    raise TypeError(msg)


class _Layout(_Block):
    """Basic building block for blockkit messages."""

    def __init__(self, block_id=None):
        super().__init__()
        self.block_id = block_id
        if self.block_id:
            self.block_id = str(block_id)

        # Validation
        if self.block_id:
            self.check_len(self, "block_id", 255)


class LayoutSection(_Layout):
    def __init__(self, text=None, fields=None, accessory=None, block_id=None):

        super().__init__(block_id)
        self.type = "section"
        self.text = text
        self.fields = fields
        self.accessory = accessory

        # Validation
        if self.text:
            self.check_instance(self, "text", _Text)
            self.check_len(self.text, "text", 3000)
        if self.fields:
            self.check_type(self, "fields", list)
            self.check_len(self, "fields", 10)
            self.check_instance_list(self, "fields", _Text)
            self.check_len_list(self, "fields", 2000)
        if self.accessory:
            self.check_instance(self, "accessory", _Element)
            # self.check_len(self, 'accessory', 1)


class LayoutDivider(_Layout):
    def __init__(self, block_id=None):

        super().__init__(block_id)
        self.type = "divider"


class LayoutImage(_Layout):
    def __init__(self, image_url, alt_text, block_id=None, title=None):

        super().__init__(block_id)
        self.type = "image"
        self.image_url = str(image_url)
        self.alt_text = str(alt_text)
        self.title = title

        # Validation
        self.check_len(self, "image_url", 3000)
        self.check_len(self, "alt_text", 2000)
        if self.title:
            self.check_instance(self, "title", TextPlain)
            self.check_len(self.title, "text", 2000)


class LayoutAction(_Layout):
    def __init__(self, elements, block_id=None):

        super().__init__(block_id)
        self.type = "actions"
        self.elements = elements

        # Validation
        self.check_type(self, "elements", list)
        self.check_len(self, "elements", 5)
        self.check_instance_list(self, "elements", _Element)


class LayoutContext(_Layout):
    def __init__(self, elements, block_id=None):

        super().__init__(block_id)
        self.type = "context"
        self.elements = elements

        # Validation
        self.check_type(self, "elements", list)
        self.check_len(self, "elements", 10)
        self.check_instance_list(self, "elements", (ElementImage, _Text))


class _Element(_Block):
    """Block Element to be  used inside section, context, and action layout blocks"""

    def __init__(self):

        super().__init__()


class ElementImage(_Element):
    def __init__(self, image_url, alt_text):

        super().__init__()
        self.type = "image"
        self.image_url = str(image_url)
        self.alt_text = str(alt_text)

        # Validation
        self.check_len(self, "image_url", 3000)
        self.check_len(self, "alt_text", 2000)


class ElementButton(_Element):
    def __init__(self, text, action_id, url=None, value=None, style=None, confirm=None):

        super().__init__()
        self.type = "button"
        self.text = text
        self.action_id = str(action_id)
        self.url = url
        self.value = value
        self.style = style
        self.confirm = confirm

        if self.url:
            str(self.url)
        if self.value:
            str(self.value)

        # Validation
        self.check_instance(self, "text", TextPlain)
        self.check_len(self.text, "text", 75)
        self.check_len(self, "action_id", 255)
        if self.url:
            self.check_len(self, "url", 3000)
        if self.value:
            self.check_len(self, "value", 75)
        if self.confirm:
            self.check_instance(self, "confirm", ObjectConfirm)


class _SelectMenu(_Element):
    def __init__(self, placeholder, action_id, confirm=None):

        super().__init__()
        self.placeholder = placeholder
        self.action_id = str(action_id)
        self.confirm = confirm

        # Validation
        self.check_instance(self, "placeholder", TextPlain)
        self.check_len(self.placeholder, "text", 150)
        self.check_len(self, "action_id", 255)
        if self.confirm:
            self.check_instance(self, "confirm", ObjectConfirm)


class SelectStatic(_SelectMenu):
    def __init__(
        self,
        placeholder,
        action_id,
        options=None,
        option_groups=None,
        initial_option=None,
        confirm=None,
    ):

        super().__init__(placeholder, action_id, confirm)
        self.type = "static_select"
        self.options = options
        self.option_groups = option_groups
        self.initial_option = initial_option

        # Validation

        # Check that only one of options/option_groups is provided
        logger.debug(
            f"Checking that {self.__class__.__name__} has one of options or option_groups"
        )
        if self.options and self.option_groups:
            msg = f"{self.__class__.__name__}.options and {self.__class__.__name__}.option_groups both specified. Only one can be specified."
            raise TypeError(msg)
        if not self.options and not self.option_groups:
            msg = f"Neither of {self.__class__.__name__}.options and {self.__class__.__name__}.option_groups was specified. Must specify one"
            raise TypeError(msg)

        if self.options:
            self.check_type(self, "options", list)
            self.check_len(self, "options", 100)
            self.check_instance_list(self, "options", ObjectOption)
            # for c, opt in enumerate(self.options):
            #     self.check_instance(self.options[c], opt, ObjectOption)
        if self.option_groups:
            self.check_type(self, "option_groups", list)
            self.check_len(self, "option_groups", 100)
            self.check_instance_list(self, "option_groups", ObjectOptionGroup)


class SelectExternal(_SelectMenu):
    def __init__(
        self,
        placeholder,
        action_id,
        initial_option=None,
        min_query_length=None,
        confirm=None,
    ):

        super().__init__(placeholder, action_id, confirm)
        self.type = "external_select"
        self.initial_option = initial_option
        self.min_query_length = int(min_query_length)


class SelectUser(_SelectMenu):
    def __init__(self, placeholder, action_id, initial_user=None, confirm=None):

        super().__init__(placeholder, action_id, confirm)
        self.type = "users_select"
        self.initial_user = initial_user

        if self.initial_user:
            self.initial_user = str(self.initial_user)


class SelectConversation(_SelectMenu):
    def __init__(self, placeholder, action_id, initial_conversation=None, confirm=None):

        super().__init__(placeholder, action_id, confirm)
        self.type = "conversations_select"
        self.initial_conversation = initial_conversation

        if self.initial_conversation:
            self.initial_conversation = str(self.initial_conversation)


class SelectChannel(_SelectMenu):
    def __init__(self, placeholder, action_id, initial_channel=None, confirm=None):

        super().__init__(placeholder, action_id, confirm)
        self.type = "channels_select"
        self.initial_channel = initial_channel

        if self.initial_channel:
            self.initial_channel = str(self.initial_channel)


class ElementOverflow(_Element):
    def __init__(self, placeholder, action_id, options, confirm=None):

        super().__init__()
        self.type = "overflow"
        self.action_id = str(action_id)
        self.options = options
        self.confirm = confirm

        # Validation
        self.check_len(self, "action_id", 255)
        if self.options:
            self.check_type(self, "options", list)
            self.check_len(self, "options", 5)
            logger.debug(
                f"Checking that {self.__class__.__name__}.options has minimum length"
            )
            if len(self.options) < 2:
                msg = f"{self.__class__.__name__}.options length should be at least 2. Provided: {self.options}"
                raise ValueError(msg)
            self.check_instance_list(self, "options", ObjectOption)
        if self.confirm:
            self.check_instance(self, "confirm", ObjectConfirm)


class ElementDatePicker(_Element):
    def __init__(self, action_id, placeholder=None, initial_date=None, confirm=None):

        super().__init__()
        self.type = "datepicker"
        self.action_id = str(action_id)
        self.placeholder = placeholder
        self.initial_date = self.initial_date
        self.confirm = confirm

        if self.initial_date:
            self.initial_date = str(self.initial_date)

        # Validation
        self.check_len(self, "action_id", 255)
        self.check_instance(self, "placeholder", TextPlain)
        self.check_len(self.placeholder, "text", 150)
        if self.initial_date:
            logger.debug(
                f"Checking that {self.__class__.__name__}.initial_date is in valid format"
            )
            r = re.compile("2[0-9]{3}-((0[1-9])|(1[0-2]))-(0[1-9]|[1-2][0-9]|3[0-1])")
            if not r.match(self.initial_date):
                msg = f"{self.__class__.__name__}.initial_date is not a valid date in the format YYYY-MM-DD. Provided: {self.initial_date}"
                raise ValueError(msg)
        if self.confirm:
            self.check_instance(self, "confirm", ObjectConfirm)


class _Object(_Block):
    """Objects which can be used inside block elements and other parts of a message."""

    def __init__(self):

        super().__init__()


class _Text(_Object):
    def __init__(self, text):

        super().__init__()
        self.text = str(text)


class TextPlain(_Text):
    def __init__(self, text, emoji=None):

        super().__init__(text)
        self.type = "plain_text"
        self.emoji = emoji

        # Validation
        if self.emoji:
            self.check_type(self, "emoji", bool)


class TextMarkdown(_Text):
    def __init__(self, text, verbatim=None):

        super().__init__(text)
        self.type = "mrkdwn"
        self.verbatim = verbatim

        # Validation
        if self.verbatim:
            self.check_type(self, "verbatim", bool)


class ObjectConfirm(_Object):
    def __init__(self, title, text, confirm, deny):

        super().__init__()
        self.title = title
        self.text = text
        self.confirm = confirm
        self.deny = deny

        # Validation
        self.check_instance(self, "title", TextPlain)
        self.check_len(self.title, "text", 100)
        self.check_instance(self, "text", _Text)
        self.check_len(self.text, "text", 300)
        self.check_instance(self, "confirm", TextPlain)
        self.check_len(self.confirm, "text", 30)
        self.check_instance(self, "deny", TextPlain)
        self.check_len(self.deny, "text", 30)


class ObjectOption(_Object):
    def __init__(self, text, value):

        super().__init__()
        self.text = text
        self.value = str(value)

        # Validation
        self.check_instance(self, "text", TextPlain)
        self.check_len(self.text, "text", 75)
        self.check_len(self, "value", 75)


class ObjectOptionGroup(_Object):
    def __init__(self, label, options):

        super().__init__()
        self.label = label
        self.options = options

        # Validation
        self.check_instance(self, "label", TextPlain)
        self.check_len(self.label, "text", 75)
        self.check_type(self, "options", list)
        self.check_instance_list(self, "options", ObjectOption)
        self.check_len(self, "options", 100)


class Bot(object):
    def __init__(
        self, subreddit, client_id, client_secret, username, password, webhook, channel
    ):
        self.logger = logger
        self.logger.info(f"Logging into /u/{username} for /r/{subreddit}")
        self.user_agent = (
            f"python3.7:Modbot for {subreddit}:v{__version__} (by /u/fwump38)"
        )
        self.r = Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=self.user_agent,
        )
        self.logger.info("Success.")
        self.subreddit_str = subreddit.lower()
        self.subreddit = self.r.subreddit(subreddit)
        self.webhook = webhook
        self.channel = channel
        self.mods = None
        self.reasons = {}
        self.report_queue = []
        self.modmail_queue_new = []
        self.modmail_queue_inprogress = []
        self.modmail_queue_notifications = []
        self.logger.info("Loading mods...")
        self.mods = list(mod.name for mod in self.subreddit.moderator())
        self.logger.info(f"Mods loaded: {self.mods}")
        self.fetch_reasons()

    def fetch_reasons(self):
        self.logger.info("Loading reasons...")
        reason_data = self.r.get(f"api/v1/{self.subreddit_str}/removal_reasons.json")
        data = reason_data["data"]
        for reason_id, values in data.items():
            regex = re.compile("[^a-zA-Z]")
            rule_name = regex.sub("", values["title"]).lower()
            self.reasons[rule_name] = {
                "message": values["message"],
                "id": values["id"],
                "title": values["title"],
            }
        self.logger.info("Reasons loaded.")

    def refresh_sub(self):
        self.logger.info(f"Refreshing subreddit: {self.subreddit_str}...")
        self.logger.info("Loading mods...")
        self.mods = list(mod.name for mod in self.subreddit.moderator())
        self.logger.info(f"Mods loaded: {self.mods}")
        self.fetch_reasons()

    def check_comments(self):
        self.logger.info(f"Checking comments...")
        for comment in self.subreddit.comments(limit=100):
            if (
                comment.banned_by
                or not comment.author
                or comment.author.name not in self.mods
            ):
                continue
            report = {
                "source": comment,
                "reason": comment.body,
                "author": comment.author.name,
            }
            self.handle_report(report, comment.parent())

    def check_reports(self):
        self.logger.info(f"Checking reports...")
        report_list = list(self.subreddit.mod.reports())
        if not report_list:
            # Clears the stored list when modqueue is emptied
            self.report_queue = []
        else:
            for submission in report_list:
                if submission not in self.report_queue:
                    self.report_queue.append(submission)
                    if submission.mod_reports:
                        report = {
                            "reason": submission.mod_reports[0][0],
                            "author": submission.mod_reports[0][1],
                        }
                        self.handle_report(report, submission)
                    elif submission.user_reports:
                        logger.info(f"Processing user report {submission}")
                        if isinstance(submission, Submission):
                            if submission.selftext:
                                content = submission.selftext
                            else:
                                content = None
                        if isinstance(submission, Comment):
                            content = submission.body
                        reason_str = "\n".join(
                            [
                                f"{reason[1]}: {reason[0]}"
                                for reason in submission.user_reports
                            ]
                        )
                        blocks = [
                            LayoutSection(
                                TextMarkdown(
                                    f":female-police-officer: *New Report:* <https://www.reddit.com{submission.permalink}|{submission.title}>"
                                )
                            )
                        ]
                        if content:
                            blocks.append(LayoutSection(TextMarkdown(f"{content}")))
                        blocks.append(
                            LayoutContext(
                                elements=[
                                    TextMarkdown(
                                        f"{'Commented by' if isinstance(submission, Comment) else 'Submitted by'} <https://www.reddit.com/u/{submission.author.name}|{submission.author.name}>"
                                    ),
                                    TextMarkdown(
                                        f"{datetime.datetime.fromtimestamp(submission.created).strftime('%c')}"
                                    ),
                                ]
                            )
                        )
                        blocks.append(
                            LayoutSection(
                                TextMarkdown(f"*User Reports:*\n{reason_str}")
                            )
                        )
                        # Post to Slack
                        slack_msg = {
                            "text": "User Report",
                            "blocks": clean(blocks),
                            "channel": self.channel,
                        }
                        r = requests.post(self.webhook, json=slack_msg)
                        if r.ok:
                            self.logger.info("Sent Report to Slack!")
                        else:
                            self.logger.error("Sending Report to Slack Failed!")
                    else:
                        continue
                else:
                    logger.debug(f"Already sent a notification about {submission}")

    def handle_report(self, report, target):
        # Check for @rule command.
        match = re.search(r"@rule (\w*) *(.*)", report["reason"], re.IGNORECASE)
        if match:
            rule = match.group(1).lower()
            note = match.group(2)
            self.logger.info(f"Rule {rule} matched.")
            if rule not in self.reasons:
                self.logger.warning(
                    f"Rule {rule} not found. Using generic rule instead."
                )
                rule = "generic"
            msg = self.reasons[rule]["message"]
            title = self.reasons[rule]["title"]
            if note:
                msg = f"{msg}\n\n{note}"

            if "source" in report:
                report["source"].mod.remove()
            target.mod.remove()

            if isinstance(target, Submission):
                self.logger.info("Removed submission.")
                permalink = target.permalink
            elif isinstance(target, Comment):
                self.logger.info("Removed comment.")
                permalink = target.permalink
            else:
                self.logger.warning(
                    "Unrecognized target type. Not instance of Comment or Submission"
                )

            # Send removal message
            target.mod.send_removal_message(msg, title=title, type="private")
            self.logger.info(f"Sent {rule} removal modmail message for {permalink}")

    def check_modmails(self):
        self.logger.info("Checking modmail...")
        new = list(self.subreddit.modmail.conversations(state="new"))
        notifications = list(
            self.subreddit.modmail.conversations(state="notifications")
        )
        inprogress = list(self.subreddit.modmail.conversations(state="inprogress"))
        # modmails = new + notifications + inprogress
        if not new:
            # Clears the stored list when new is emptied
            self.modmail_queue_new = []
        if not inprogress:
            # Clears the stored list when inprogress is emptied
            self.modmail_queue_inprogress = []
        if not notifications:
            # Clears the stored list when notifications is emptied
            self.modmail_queue_notifications = []

        send_to_slack = []
        for modmail in new:
            if modmail.messages[-1].author.name in self.mods:
                modmail.archive()  # Auto-archive mod messages (removal messages)
                message = modmail.messages[0]
                match = re.search(
                    r"Original (post|comment): (.*)",
                    message.body_markdown,
                    re.IGNORECASE,
                )
                if match:
                    removal_type = match.group(1).lower()
                    permalink = match.group(2)
                    # Post to Slack
                    blocks = [
                        LayoutSection(
                            TextMarkdown(
                                f":no_entry_sign: {message.author.name} removed {removal_type} <https://www.reddit.com{permalink}>"
                            )
                        )
                    ]
                    # Post to Slack
                    slack_msg = {
                        "text": "New Modmail",
                        "blocks": clean(blocks),
                        "channel": self.channel,
                    }
                    r = requests.post(self.webhook, json=slack_msg)
                    if r.ok:
                        self.logger.info("Sent Report to Slack!")
                    else:
                        self.logger.error("Sending Report to Slack Failed!")
            else:
                if modmail not in self.modmail_queue_new:
                    self.modmail_queue_new.append(modmail)
                    send_to_slack.append(modmail)
        for modmail in inprogress:
            if modmail.messages[-1].author.name in self.mods:
                pass
            else:
                if modmail not in self.modmail_queue_inprogress:
                    self.modmail_queue_inprogress.append(modmail)
                    send_to_slack.append(modmail)
        for modmail in notifications:
            if modmail.messages[0].author.name == "AutoModerator":
                if modmail not in self.modmail_queue_notifications:
                    self.modmail_queue_notifications.append(modmail)
                    send_to_slack.append(modmail)
            else:
                modmail.archive()  # Auto-archive other notifications

        for modmail in send_to_slack:
            messages = []
            latest = modmail.messages[-1]
            blocks = [
                LayoutSection(
                    TextMarkdown(
                        f":email: *New Modmail:* <https://mod.reddit.com/mail/all/{modmail.id}|{modmail.subject}>\n{latest.body_markdown}"
                    )
                ),
                LayoutContext(
                    elements=[
                        TextMarkdown(
                            f"from <https://www.reddit.com/u/{latest.author.name}|{latest.author.name}>"
                        )
                    ]
                ),
            ]
            # Post to Slack
            slack_msg = {
                "text": "New Modmail",
                "blocks": clean(blocks),
                "channel": self.channel,
            }
            r = requests.post(self.webhook, json=slack_msg)
            if r.ok:
                self.logger.info("Sent Report to Slack!")
            else:
                self.logger.error("Sending Report to Slack Failed!")

    def check_mail(self):
        self.logger.info("Checking mail...")
        for mail in self.r.inbox.unread():
            mail.mark_read()
            self.logger.info(f'New mail: "{mail.body}".')
            match = re.search(r"@refresh (.*)", mail.body, re.IGNORECASE)
            if not match:
                continue
            subreddit = match.group(1).lower()
            if subreddit == self.subreddit:
                if mail.author.name in self.mods:
                    self.refresh_sub(subreddit)
                    mail.reply(f"Refreshed mods and reasons for {subreddit}!")
                else:
                    mail.reply((f"Unauthorized: not an r/{subreddit} mod"))
            else:
                mail.reply(f"Unrecognized sub:  {subreddit}.")

    def run(self):
        while True:
            self.logger.info("Running cycle...")
            try:
                self.check_comments()
                self.check_reports()
                self.check_modmails()
                self.check_mail()
            except Exception as exception:
                self.logger.exception(exception)
            self.logger.info("Sleeping...")
            time.sleep(32)  # PRAW caches responses for 30s.


if __name__ == "__main__":

    modbot = Bot(
        subreddit=os.getenv("SUBREDDIT"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        password=os.getenv("MOD_PASSWORD"),
        username=os.getenv("MOD_USERNAME"),
        webhook=os.getenv("WEBHOOK"),
        channel=os.getenv("CHANNEL", "#submission_feed"),
    )
    modbot.run()
