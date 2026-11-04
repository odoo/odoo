# Environment and Delivery Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md` |
| Artifact owner | Program delivery lead |
| Required reviewers | Program engineering lead, architecture lead, security reviewer |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before release planning, before environment promotion, and whenever access or delivery controls change |
| Last updated | 2026-11-04 |

## Purpose

Define the operating contract for each environment, who may change it, what evidence is needed for promotion, and which delivery controls must be satisfied before work can move forward.

## Scope

- Applies to Local Dev, Shared Dev / Integration, Test / QA, UAT / Training, and Production for the Odoo 19 CE Enterprise program.
- Applies to configuration changes, data handling, releases, hotfixes, rollback readiness, and environment access decisions.
- Works together with `engineering-standards.md` for build quality and `review-gates.md` for gate decisions.

## Environment Model

| Environment | Primary purpose | Allowed data | Who may change it | Promotion expectation |
| --- | --- | --- | --- | --- |
| Local Dev | Isolated development and debugging | Synthetic or safely masked data only | Assigned implementer on their own workspace | Must not be treated as evidence of shared readiness on its own |
| Shared Dev / Integration | Combined technical validation across teams and addons | Synthetic, masked, or approved integration data | Engineering team through reviewed change flow | Must show integration stability before QA promotion |
| Test / QA | Formal test execution and defect confirmation | Approved test dataset with stable scenarios | QA or delivery-authorized operators only | Must show repeatable test evidence and resolved blocking defects |
| UAT / Training | Business validation, training rehearsal, and operating acceptance | Approved business-like data, masked where required | Delivery lead or delegated release operator | Must show business acceptance and training readiness before production |
| Production | Live service delivery | Live operational data only | Authorized production operators under approved release control | Requires explicit go-live or release approval with rollback readiness |

## Access and Data Controls

| Environment | Access expectation | Prohibited behavior | Decision rule |
| --- | --- | --- | --- |
| Local Dev | Individual implementer and reviewers supporting the active task | Using live production credentials or unmasked production extracts | If live data is needed, stop and require security-approved masking or alternative evidence. |
| Shared Dev / Integration | Engineers, reviewers, and automation needed for integration checks | Ad hoc data fixes with no record, uncontrolled config drift | If a change affects another team, it must be reviewable and announced before merge or deployment. |
| Test / QA | QA, delivery, and reviewers validating the release slice | Feature experimentation unrelated to the approved test scope | If a test environment is unstable, promotion stops until the environment is restored and evidence is rerun. |
| UAT / Training | Named business validators, trainers, delivery lead, and support staff | Unapproved schema changes, debugging directly against business validation data | If business users cannot reproduce the approved scope reliably, UAT cannot be treated as passed. |
| Production | Named operators, responders, and approvers with least privilege | Trial-and-error debugging, direct experimentation, and undocumented fixes | If the planned change cannot be executed through a controlled release path, it is not production-ready. |

## Delivery Baseline

- Every merge that affects shared environments must link to the approved scope, review evidence, and relevant quality results.
- Every deployment must include a release note, execution owner, rollback expectation, and post-deploy verification responsibility.
- Every promotion must name the release tag it deploys; a branch head is not an acceptable release artifact.
- Production is never a testing ground for unreviewed behavior, schema experiments, or undocumented operational fixes.
- Emergency changes may shorten the path but cannot skip owner identification, change recording, or rollback planning.

## Release Tag Control

- Releases are cut as annotated tags `v19.0.<n>` on the `19.0` trunk; deployments check out a tag, never a branch head.
- Each tag is the immutable evidence anchor for promotion: the promotion record must cite the tag and its commit SHA.
- Runtime configuration and install steps for a release come from that tag's `deployment/` package (`odoo.conf.template`, `install.sh`, `systemd/odoo19.service`).
- A tag is immutable once pushed; corrections ship as the next tag (`v19.0.<n+1>`), never by moving or re-pointing an existing tag.
- Addons are delivered from the tag's `custom_addons/` tree with OCA submodules resolved to their pinned commit SHAs.

## Promotion Control Block

| Promotion | Required evidence | Stop conditions |
| --- | --- | --- |
| Local Dev -> Shared Dev / Integration | Peer-reviewed change, lint results, targeted tests, and no known install breakage | The change is only verified on one machine, depends on local-only configuration, or lacks a reviewable diff. |
| Shared Dev / Integration -> Test / QA | Integration validation complete, key flows stable, dependency changes documented | Cross-team regressions remain open, environment drift is unresolved, or setup instructions are incomplete. |
| Test / QA -> UAT / Training | QA evidence complete, blocking defects closed or explicitly waived, training-impact notes available | Critical defects remain unresolved, evidence is not repeatable, or business scenarios are still ambiguous. |
| UAT / Training -> Production | Business acceptance, release note, rollback plan, support owner, and release window approval | Acceptance is partial without bounded follow-up, rollback is untested, or support ownership is unclear. |

## Minimum Quality Gates

| Control | Minimum expectation | Review use |
| --- | --- | --- |
| Lint | Relevant static checks pass for the delivery scope | Gate 4 build evidence |
| Automated tests | Critical path automation passes with reviewable output | Gate 4 and release readiness |
| Install/uninstall checks | Addons in scope install, upgrade, and uninstall safely in a controlled environment | Gate 4 build evidence |
| Security review | Access rights, secrets handling, and privileged behavior reviewed | Gate 4 and production approval |
| Upgrade note | Delivery impact and follow-up expectations documented | Release planning and rollback review |

## Release Decision Rules

- Approve release only when the target environment has named owners, required evidence, and a bounded rollback path.
- Delay release when evidence exists but still depends on manual tribal knowledge that is not recorded in the release note or runbook.
- Reject release when the same package still requires ad hoc fixes in the target environment to become deployable.
- Treat environment drift as a blocker, not a note, whenever it changes the meaning of test or acceptance evidence.

## Exception Path

- Access or promotion exceptions must be explicit, time-bounded, and approved by the environment owner plus the relevant reviewer.
- Exceptions cannot be used to normalize production testing, remove rollback expectations, or bypass security review for shared or live environments.
- Every exception record must state the affected environment, rationale, mitigation, owner, expiry date, and re-review point.

## Review Cadence

- Reconfirm this baseline before each major promotion and at every release planning checkpoint.
- Review after any incident caused by environment drift, access gaps, or failed rollback.
- Update the policy when the program standardizes a new promotion, support, or access pattern.
