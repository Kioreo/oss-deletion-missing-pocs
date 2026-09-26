# Discourse

Deletion-residue test cases for Discourse. The current public set contains reports 2 and 3; the report numbers are retained here for cross-reference but are not used as directory names.

| Report | Directory | Summary |
| --- | --- | --- |
| 2 | [`account-deletion-orphaned-references`](account-deletion-orphaned-references/) | Self-service account deletion may leave user-linked database rows |
| 3 | [`review-queue-retains-deleted-post-body`](review-queue-retains-deleted-post-body/) | Review queue data may retain the original body after author deletion |

Test only against an authorized disposable instance. Exact affected versions and upstream report links should be added when disclosure is approved.
