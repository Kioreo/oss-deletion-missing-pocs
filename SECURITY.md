# Security and responsible use

This repository contains security test cases, not a target list or authorization to test public services.

- Run PoCs only on systems you own or are explicitly authorized to assess.
- Use disposable accounts and synthetic marker data.
- Do not commit credentials, cookies, tokens, database dumps, hostnames of private systems, or user data.
- Report newly discovered issues privately to the affected maintainers before adding them here.
- If this repository itself exposes a secret or unsafe artifact, contact the repository owner privately instead of opening a public issue.

## Before publishing a finding

Move each finding through private draft, reported, maintainer acknowledged, disclosure approved or fix released, and only then public. Follow the affected project's security policy and coordinate the publication date with its maintainers.

Record the upstream report URL or private report identifier, affected and tested versions, fix status, and disclosure date in the finding README. Review code, logs, screenshots, HTTP captures, and database output for credentials, tokens, cookies, email addresses, IP addresses, private hostnames, and unrelated user content.
