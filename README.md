# docker-modbot
Moderate subreddits with simple commands and be notified about modmail and user reports through Slack!

Usage
=====

Modbot can be invoked by any comment or moderator report containing one of
the following commands:

- ``@rule {reason} [note]``: **removes a thread, leaving an appropriate flair
  and comment**. ``reason`` is one of the removal reasons' keys (see `Removal
  reasons`_). If no corresponding removal reason is found, the ``Generic``
  reason is used instead. If ``note`` is provided, it will be added to the
  message.

  Example: ``@rule 1``, ``@rule spam``, ``@rule repost this is a note``.

- **Refreshing the list of moderators/removal reasons**:

  Modbot loads the subreddit's list of moderators and removal reasons at
  startup. To refresh these, send the Modbot account a message containing ``@refresh
  Subreddit`` (e.g. ``@refresh Android`` to reload ``/r/Android``'s
  configuration).

Only moderator reports and comments made by/mails sent by the subreddit's
moderators are checked.

PS. Reddit silently ignores reports on removed posts, so Modbot won't see
those.

Setup
=====

Dependencies
------------

Modbot requires Python 3. For a list of required Python 3 libraries, see
``requirements.txt``.

Requirements
------------

You'll first want to create a new account and make it a mod of your subreddit.
Required permissions are: access, flair, posts, mail, and wiki.

Next you'll need to setup a Script app for your bot to access the Reddit API. See [Reddit Quick Start](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps)

Finally, if not already, create a free Slack team. This is used to send alerts about new modmails or user reports and works in conjunction with fwump38/docker-submissionbot to keep you up to date with posts as they happen. Once you have a Slack team, you'll need to add an [Incoming Webhook](https://api.slack.com/incoming-webhooks)

Configuration
-------------

Modbot uses environment variables in it's docker run command for configuration.

```shell
docker run -t -i -d \
  -e CLIENT_ID=xxxxxxx \
  -e CLIENT_SECRET=xxxxxxx \
  -e SUBREDDIT=some_subreddit \
  -e MOD_USERNAME=some_user \
  -e MOD_PASSWORD=xxxxxxx \
  -e WEBHOOK=xxxxxxx \
  fwump38/docker-modbot
```

### Parameters

* `-e CLIENT_ID` - The Client ID of the Reddit Bot that will be used. **Required**
* `-e CLIENT_SECRET` - The Client Secret of the Reddit Bot that will be used. **Required**
* `-e SUBREDDIT` - The name of the subreddit to monitor. **Required**
* `-e MOD_USERNAME` - The Reddit account name of the bot. **Required**
* `-e MOD_PASSWORD` - The password to the Reddit account. **Required**
* `-e WEBHOOK` - The URL for a Slack Incoming Webhook. **Required**
* `-e CHANNEL` - The Slack Channel to send Submissions to - defaults to #submission_feed otherwise **Optional**

**Note:** To run Modbot with multiple subreddits, you will need to spin up additional docker containers. 
This can be simplified using a docker-compose file with each subreddit as it's own service with their own environment variables. See the example [docker-compose](docker-compose.yml.example) file.

Removal reasons
-------------

Modbot uses the new style of Removal Reasons built into Reddit. To edit them visit: https://www.reddit.com/r/YOURSUBREDDIT/about/removal (replacing the subreddit with your own)

At the very least, you **MUST** create a removal reason with the following details:
- **Title:** Genric
- **Message:** Please review our sidebar for the complete list of rules.

If the rule command does not match a given rule (due to typo or otherwise) it will still remove the post/comment using this generic removal reason.

**NOTE**: When making titles for your removals, keep the following in mind:

- Any whitespace, numbers, or non alphabet characters will be stripped out

For example:

This | Becomes
--- | ---
Search | search
Be Kind | bekind
Buy/Sell | buysell
Search2 | search (This one will cause an error since two titles share the same "key")

