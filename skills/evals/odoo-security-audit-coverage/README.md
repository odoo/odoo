# odoo-security-audit-coverage

Security review of a synthetic module where every pattern of the
odoo-security skill is planted.

- Checkout: a new `property_rental` module (properties, leases, a tenant
  portal) committed on branch `20.0-property-rental-jdoe`. It installs and
  runs; nothing in it hints at the planted issues.
- Instruction: review the module before the PR, write the findings to
  `/app/security_review.md`, do not change the module.
- Planted: 28 issues, at least one per section and sweep pattern of the
  skill (access rows, field groups, related sudo, public methods, SQL, domain
  injection, sudo, routes and CSRF, XSS in Python, QWeb and JS, open, eval,
  pickle, getattr, timing, mutable defaults, returned objects), next to four
  correct constructs that must not be reported. The answer key is
  `solution/security_review.md`, which the oracle writes as its review.
- Graded on:
  - the findings: one judge criterion per planted issue (recall), no false
    positives on the correct constructs, severity, location and fix given;
  - the structure: the review is written, the module and branch unchanged;
  - the process: review only, honest final reply.
