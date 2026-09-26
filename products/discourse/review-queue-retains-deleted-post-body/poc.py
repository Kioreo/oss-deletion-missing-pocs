"""Reproduces review-queue retention of a queued post body after the author deletes it.

Use only against a system where you are authorized to test. This script has no
command-line options. Edit the constants below, then run `python3 poc.py`.

It needs two accounts: a normal author whose posts are sent to the approval
queue, and a staff/admin account that can approve and read the review queue.
It creates one test topic, approves it, deletes it as its author, and then
checks whether the review queue still serves the original body. It changes no
site settings and touches nothing it did not create.

Precondition, set by an admin before running: the author's posts must be
queued for approval, e.g. `approve post count` = 5 with `trust_level_0`
removed from `approve unless allowed groups`.

Requirement: requests
"""

import secrets

import requests


# Edit these values for the authorized target. No command-line options are used.
BASE_URL = "http://localhost:3000"
AUTHOR_USERNAME = "replace-with-your-queued-test-user"
AUTHOR_PASSWORD = "replace-with-that-password"
STAFF_USERNAME = "replace-with-your-staff-user"
STAFF_PASSWORD = "replace-with-that-password"
# Leave as None to pick the first category the author may post in.
CATEGORY_ID = None

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
    if not response.json().get("user", {}).get("username"):
        raise RuntimeError(f"Login response for {username} did not contain a user.")
    return session


def first_writable_category(session):
    response = require(
        session.get(f"{BASE_URL}/categories.json", timeout=TIMEOUT),
        {200},
        "list categories",
    )
    for category in response.json()["category_list"]["categories"]:
        if category.get("permission") != 0 and not category.get("read_restricted"):
            return category["id"]
    raise RuntimeError("No writable public category was found for this account.")


def main():
    if "replace-with" in AUTHOR_USERNAME or "replace-with" in STAFF_USERNAME:
        raise RuntimeError("Edit the account constants at the top of this file first.")

    globals()["BASE_URL"] = BASE_URL.rstrip("/")
    body_marker = f"QUEUED-BODY-{secrets.token_hex(10)}"
    title_marker = f"QUEUED-TITLE-{secrets.token_hex(8)}"

    author = login(AUTHOR_USERNAME, AUTHOR_PASSWORD)
    staff = login(STAFF_USERNAME, STAFF_PASSWORD)
    category_id = CATEGORY_ID or first_writable_category(author)

    created = require(
        author.post(
            f"{BASE_URL}/posts.json",
            data={
                "title": f"Authorized queue test {title_marker}",
                "raw": f"Body marker: {body_marker}. " + "padding " * 6,
                "category": category_id,
                "archetype": "regular",
            },
            headers=headers(author),
            timeout=TIMEOUT,
        ),
        {200},
        "create the test topic",
    ).json()

    if created.get("action") != "enqueued":
        raise RuntimeError(
            "Precondition not met: the post was published directly instead of being "
            "queued. Ask an admin to route this account's posts to the approval queue."
        )
    reviewable_id = created["pending_post"]["id"]

    require(
        staff.put(
            f"{BASE_URL}/review/{reviewable_id}/perform/approve_post.json?version=0",
            headers=headers(staff),
            timeout=TIMEOUT,
        ),
        {200},
        "approve the queued post",
    )

    shown = require(
        staff.get(f"{BASE_URL}/review/{reviewable_id}.json", timeout=TIMEOUT),
        {200},
        "read the approved reviewable",
    ).json()
    topic_id = (shown.get("topic_id")
                or shown.get("reviewable", {}).get("topic_id")
                or (shown.get("topics") or [{}])[0].get("id"))
    if not topic_id:
        raise RuntimeError("Could not determine the topic created from the queued post.")

    require(
        author.delete(
            f"{BASE_URL}/t/{topic_id}.json",
            headers=headers(author),
            timeout=TIMEOUT,
        ),
        {200},
        "delete the approved topic as its author",
    )

    anonymous = requests.Session()
    anonymous.headers.update({"User-Agent": "authorized-security-test/1.0"})
    public = require(
        anonymous.get(f"{BASE_URL}/t/{topic_id}.json", timeout=TIMEOUT),
        {200, 403, 404},
        "anonymous post-delete topic read",
    )
    if public.status_code == 200 and body_marker in public.text:
        raise RuntimeError(
            "Not reproduced: the public topic still carries the body; the author "
            "deletion did not take effect."
        )

    queue = require(
        staff.get(f"{BASE_URL}/review.json?status=all", timeout=TIMEOUT),
        {200},
        "read the review queue as staff",
    )
    if body_marker not in queue.text:
        raise RuntimeError(
            "Not reproduced: the review queue no longer contains the original body."
        )

    scrub = staff.put(
        f"{BASE_URL}/review/{reviewable_id}/scrub.json",
        data={"reason": "the author deleted this post"},
        headers=headers(staff),
        timeout=TIMEOUT,
    )

    print("REPRODUCED")
    print(f"Author deletion of topic {topic_id} returned HTTP 200.")
    print(f"The public topic no longer carries the body (HTTP {public.status_code}).")
    print(
        f"Staff GET /review.json?status=all still returns the original body of "
        f"reviewable {reviewable_id}: {body_marker}"
    )
    print(
        f"Admin PUT /review/{reviewable_id}/scrub.json -> HTTP {scrub.status_code} "
        "(only rejected ReviewableUser records are scrubbable)"
    )
    print("The script created and deleted only this test topic.")

    # Optional maintainer-side confirmation (not sent to the remote service):
    # SELECT id, type, status, payload::text FROM reviewables WHERE id = <reviewable_id>;
    # payload->>'raw' still holds the body the author deleted.


if __name__ == "__main__":
    main()
