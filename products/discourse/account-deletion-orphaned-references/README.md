# Account deletion leaves user-linked rows

**Internal report:** Discourse #2  
**Disclosure status:** Maintainer requested a public PoC link; add the upstream topic URL and tested version before publishing.

## Summary

After a user completes normal self-service account deletion, rows in several tables may still reference that user's numeric ID. The PoC creates narrowly scoped activity for a disposable account, deletes that account, and prints operator-side SQL used to check for residue.

## Safety warning

`poc.py` permanently deletes the configured account. Use a disposable account with no posts and a disposable, authorized test instance. The script does not connect to the database and does not delete unrelated content.

## Prerequisites

- Python 3 and `requests`
- A disposable user with no posts or topics
- One readable public topic
- A second existing username, used only as a share-link parameter
- Operator access to run the printed read-only SQL after deferred jobs finish

## Run

Edit only the placeholder constants at the top of `poc.py`, read the warning again, set `CONFIRM_DELETE_ACCOUNT = True`, then run:

```bash
python3 poc.py
```

## Expected result

The self-service deletion succeeds and the profile is no longer available. After deferred jobs drain, one or more of the printed read-only queries demonstrates whether a user-linked row remains. A finding should be claimed only from the database result, not merely from the successful account deletion.

## Cleanup

The configured user is already permanently deleted. Remove synthetic test residue only through the maintainer-approved administrative procedure for the test instance.
