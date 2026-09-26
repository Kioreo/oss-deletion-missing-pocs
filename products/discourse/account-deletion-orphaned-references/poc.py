"""Reproduces rows that still point at a user after they delete their own account.

Use only against a system where you are authorized to test. This script has no
command-line options. Edit the constants below, then run `python3 poc.py`.

It uses a disposable account that owns no posts, so it works under the default
`delete user self max post count`. It performs one search and two topic visits
as that account, then deletes the account through the normal self-service
endpoint. The residue itself lives in the database, so the script prints the
exact SQL an operator should run afterwards; it never connects to the database.

THIS SCRIPT PERMANENTLY DELETES THE ACCOUNT IT IS GIVEN. Use a disposable one.

Requirement: requests
"""

import secrets

import requests


# Edit these values for the authorized target. No command-line options are used.
BASE_URL = "http://localhost:3000"
# A disposable account that owns no posts. It WILL be deleted by this script.
SUBJECT_USERNAME = "replace-with-your-disposable-test-user"
SUBJECT_PASSWORD = "replace-with-that-password"
# Any public topic id on the site that the subject can read, and its slug.
TOPIC_ID = None
TOPIC_SLUG = None
# Any other existing username, used only as the share parameter on one visit.
OTHER_USERNAME = "replace-with-any-other-username"
# Set to True once you have read the warning above.
CONFIRM_DELETE_ACCOUNT = False

TIMEOUT = 20


def require(response, expected_statuses, action):
    if response.status_code not in expected_statuses:
        raise RuntimeError(
            f"{action} failed: HTTP {response.status_code}\n{response.text[:1000]}"
        )
    return response


def csrf(session):
    return require(
        session.get(f"{BASE_URL}/session/csrf.json", timeout=TIMEOUT),
        {200},
        "fetch CSRF token",
    ).json()["csrf"]


def headers(session):
    return {"X-CSRF-Token": csrf(session), "X-Requested-With": "XMLHttpRequest"}


def login(username, password):
    session = requests.Session()
    session.headers.update({"User-Agent": "authorized-security-test/1.0"})
    response = require(
        session.post(
            f"{BASE_URL}/session",
            data={"login": username, "password": password},
            headers=headers(session),
            timeout=TIMEOUT,
        ),
        {200},
        f"login {username}",
    )
    user = response.json().get("user", {})
    if not user.get("username"):
        raise RuntimeError(f"Login response for {username} did not contain a user.")
    return session


def first_public_topic(session):
    listing = require(
        session.get(f"{BASE_URL}/latest.json", timeout=TIMEOUT), {200}, "list topics"
    ).json()
    for topic in listing["topic_list"]["topics"]:
        if not topic.get("closed") and topic.get("slug"):
            return topic["id"], topic["slug"]
    raise RuntimeError("No readable topic was found to use for the link probe.")


def main():
    if "replace-with" in SUBJECT_USERNAME or "replace-with" in OTHER_USERNAME:
        raise RuntimeError("Edit the account constants at the top of this file first.")
    if not CONFIRM_DELETE_ACCOUNT:
        raise RuntimeError(
            "Set CONFIRM_DELETE_ACCOUNT = True. This script deletes SUBJECT_USERNAME."
        )

    globals()["BASE_URL"] = BASE_URL.rstrip("/")
    term = f"DELETIONPROBE{secrets.token_hex(8)}"

    subject = login(SUBJECT_USERNAME, SUBJECT_PASSWORD)
    me = require(
        subject.get(f"{BASE_URL}/u/{SUBJECT_USERNAME}.json", timeout=TIMEOUT),
        {200},
        "read own profile",
    ).json()["user"]
    subject_id = me["id"]
    if me.get("post_count", 0) or me.get("topic_count", 0):
        raise RuntimeError(
            "Use an account that owns no posts, so the default "
            "`delete user self max post count` still permits self-deletion."
        )

    topic_id, topic_slug = (TOPIC_ID, TOPIC_SLUG)
    if not topic_id or not topic_slug:
        topic_id, topic_slug = first_public_topic(subject)

    # search_logs row for this user
    require(
        subject.get(f"{BASE_URL}/search.json?q={term}", timeout=TIMEOUT),
        {200},
        "run a search as the subject",
    )

    # incoming_links row with current_user_id = subject
    require(
        subject.get(
            f"{BASE_URL}/t/{topic_slug}/{topic_id}?u={OTHER_USERNAME}",
            headers={"Referer": "https://external-referer.invalid/subject-click"},
            allow_redirects=False,
            timeout=TIMEOUT,
        ),
        {200},
        "visit a topic as the subject from an external referer",
    )

    # incoming_links row with user_id = subject (an anonymous visitor follows the
    # subject's share link)
    anonymous = requests.Session()
    anonymous.headers.update({"User-Agent": "authorized-security-test/1.0"})
    require(
        anonymous.get(
            f"{BASE_URL}/t/{topic_slug}/{topic_id}?u={SUBJECT_USERNAME}",
            headers={"Referer": "https://external-referer.invalid/anon-click"},
            allow_redirects=False,
            timeout=TIMEOUT,
        ),
        {200},
        "visit a topic anonymously via the subject's share link",
    )

    deleted = require(
        subject.delete(
            f"{BASE_URL}/u/{SUBJECT_USERNAME}.json",
            data={"context": "/my/preferences/account"},
            headers=headers(subject),
            timeout=TIMEOUT,
        ),
        {200},
        "self-service account deletion",
    )

    gone = requests.get(
        f"{BASE_URL}/u/{SUBJECT_USERNAME}.json",
        headers={"User-Agent": "authorized-security-test/1.0"},
        timeout=TIMEOUT,
    )

    print("ACCOUNT DELETION ACCEPTED")
    print(f"DELETE /u/{SUBJECT_USERNAME}.json -> HTTP {deleted.status_code} {deleted.text.strip()}")
    print(f"GET /u/{SUBJECT_USERNAME}.json afterwards -> HTTP {gone.status_code}")
    print(f"deleted user id: {subject_id}")
    print(f"search term used: {term}")
    print()
    print("Wait for the deferred jobs to drain, then run these as the operator.")
    print("Each should return zero rows after a complete deletion:")
    print()
    print(f"  SELECT id, user_id, current_user_id, ip_address, post_id")
    print(f"    FROM incoming_links")
    print(f"   WHERE user_id = {subject_id} OR current_user_id = {subject_id};")
    print()
    print(f"  SELECT id, user_id, term FROM search_logs WHERE user_id = {subject_id};")
    print()
    print(f"  SELECT id, user_id FROM topics WHERE user_id = {subject_id};")
    print(f"  SELECT id, post_id, user_id FROM post_revisions WHERE user_id = {subject_id};")
    print(f"  SELECT id, name, user_id FROM custom_emojis WHERE user_id = {subject_id};")
    print(f"  SELECT id, localizer_user_id FROM topic_localizations")
    print(f"   WHERE localizer_user_id = {subject_id};")
    print(f"  SELECT id, user_id FROM policy_users WHERE user_id = {subject_id};")
    print()
    print("A generic sweep over every user-ish integer column:")
    print(
        "  SELECT c.table_name, c.column_name FROM information_schema.columns c\n"
        "    JOIN information_schema.tables t\n"
        "      ON t.table_name = c.table_name AND t.table_schema = c.table_schema\n"
        "   WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'\n"
        "     AND c.data_type IN ('integer','bigint')\n"
        "     AND c.column_name ~ 'user' AND c.column_name ~ 'id$';"
    )
    print(f"  -- then count rows equal to {subject_id} in each of those columns.")
    print()
    print("The script created no topics and deleted only the account it was given.")


if __name__ == "__main__":
    main()
