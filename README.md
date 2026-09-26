# OSS Deletion Missing PoCs

Proof-of-concept scripts for deletion-related issues reported to open-source projects. Each finding documents data that remains accessible or referenced after the corresponding content or account is deleted.

Use these scripts only on a local instance or a system where you have explicit permission to test. Read the finding-specific README before running a PoC because some tests perform irreversible deletion.

## Repository layout

```text
products/
  <project>/
    README.md
    <finding-slug>/
      README.md
      poc.py
```

Projects are grouped under `products/`, with one directory per independently reproducible finding. Future projects can be added as peers, such as `products/mastodon/` and `products/gitlab/`.
