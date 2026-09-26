# Review queue retains a deleted post body

**Internal report:** Discourse #3  
**Disclosure status:** Maintainer requested a public PoC link; add the upstream topic URL and tested version before publishing.

## Summary

A post routed through approval can remain in review data after it is approved and later deleted by its author. The PoC checks whether staff review endpoints still return the original synthetic body marker after the public topic no longer does.

## Prerequisites

- Python 3 and `requests`
- An authorized disposable Discourse instance
- A normal test author whose posts enter the approval queue
- A staff test account able to approve posts and read the review queue
- A writable public category

One possible test setup is `approve post count = 5` with `trust_level_0` removed from `approve unless allowed groups`. Restore any test-only site setting afterwards.

## Run

Edit only the placeholder constants at the top of `poc.py`, then run:

```bash
python3 poc.py
```

## Expected result

The PoC creates and approves one synthetic topic, deletes that topic as its author, confirms the marker is absent publicly, then checks whether the staff review response still contains it. It also reports the result of the review scrub endpoint.

## Cleanup

The PoC deletes only the topic it creates. Restore any approval-queue setting changed for the test and remove residual review data only through a maintainer-approved procedure.
