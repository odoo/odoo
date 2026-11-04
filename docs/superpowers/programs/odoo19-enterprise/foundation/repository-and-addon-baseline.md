# Repository and Addon Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md` |
| Artifact owner | Program engineering lead |
| Required reviewers | Architecture lead, delivery lead, security reviewer |
| Artifact status | Active baseline |
| Review cadence | Reconfirm before each domain build starts and whenever repository structure or addon boundaries change |
| Last updated | 2026-11-04 |

## Purpose

Define where delivery artifacts belong, how addon boundaries are evaluated, and which controls must be satisfied before a repository or module change can pass review.

## Scope

- Applies to program documentation, custom addons, selected OCA addons, approved third-party dependencies, deployment assets, migration utilities, and automation artifacts produced for this program.
- Applies from Wave 0 foundation through each domain implementation and production cutover preparation.
- Works together with `docs/superpowers/programs/odoo19-enterprise/foundation/engineering-standards.md` and `docs/superpowers/programs/odoo19-enterprise/governance/review-gates.md`; this document does not waive any rule defined there.

## Repository Layout Rules

The repository is a disciplined monorepo: the upstream Odoo tree and the program's own delivery areas live side by side but have separate ownership. The upstream area must stay mergeable with `odoo/odoo` and is never the target of program edits.

### Upstream area — mirror-owned, read-only

| Path | Intended contents | Control rule |
| --- | --- | --- |
| `odoo/` | Odoo core framework | Never edit. Changes arrive only through merges from `upstream/19.0`. |
| `addons/` | Odoo core addons | Never edit. Same merge-only rule as `odoo/`. |
| `setup/`, `debian/`, `doc/` | Upstream packaging and documentation | Reserved upstream paths; never edit. |

### Program area — team-owned

| Path or area | Intended contents | Control rule |
| --- | --- | --- |
| `docs/` | Specs, plans, governance, reporting, discovery, and review evidence | Documentation must remain reviewable, versioned, and linked from the relevant program artifact. |
| `custom_addons/` | Company-specific addons approved after standard and OCA evaluation | Every addon must map to an approved domain scope and satisfy install, upgrade, and uninstall safety. |
| `third_party/oca/` | OCA addons reused as pinned git submodules | Keep provenance visible; pin by commit SHA in `.gitmodules` and never declare `branch =`. |
| `deployment/` | Runtime configuration templates, service units, install script, runbook, release notes | Owned by the delivery lead. Must not embed live secrets and must support rollback planning. |
| `migration/` | Odoo 15 → 19 migration utilities and reconciliation artifacts | Migration-only helpers stay here, never inside unrelated business addons. |
| `backups/` | Local dump/bundle archives (git-ignored) | Never committed; restore procedure is recorded in the rollback note. |
| `tests/` or addon-local test paths | Automated tests, fixtures, and verification helpers | Test evidence must be traceable to the domain or baseline under review. |

### Path Ownership

- Upstream paths (`odoo/`, `addons/`, `setup/`, `debian/`, `doc/`) are owned by the Odoo merge flow; program work must never modify them.
- Program paths (`custom_addons/`, `deployment/`, `docs/`, `migration/`) are owned by the program team and follow the review gates in this baseline.
- The first-party `deployment/` package is the only supported way to install the stack onto another server; the reference procedure is `deployment/README.md`, released through tags only.
- A change that must cross the ownership boundary is a structural exception and requires architecture lead sign-off.

## Addon Boundary Rules

- One addon owns one primary responsibility and one bounded business capability.
- Dependencies must be declared in the addon manifest and justified in review notes when they add non-obvious coupling.
- Hidden coupling is not allowed; integrations must be discoverable through explicit dependencies, service interfaces, or documented extension points.
- Every addon must be safe to install, upgrade, and uninstall in an isolated environment before it can pass Gate 4 review.
- Addons that only exist to bypass a poor boundary are not acceptable; the scope must be split or redesigned instead.

## Addon Admission Controls

| Decision question | Pass condition | Escalate or fail when |
| --- | --- | --- |
| Should this be a new addon? | The scope is a distinct business capability, cannot be absorbed cleanly into an approved existing addon, and has its own manifest-level lifecycle. | The change is only a minor extension of an existing bounded addon or exists only because ownership is unclear. |
| Should the program use OCA instead of custom code? | Standard Odoo and OCA options were evaluated first and either selected or rejected with written rationale. | No evaluation record exists or the team jumps directly to custom implementation. |
| Is the addon boundary acceptable? | Responsibilities, data ownership, and interfaces can be explained without reading unrelated modules. | The addon mixes multiple domains, depends on undocumented side effects, or requires coordinated deployment with unrelated modules. |
| Is the addon ready for build approval? | Naming, dependencies, install/uninstall safety, and traceability back to the approved spec are all evidenced. | Any one of those controls is missing, implicit, or contradictory. |

## Naming and Traceability Rules

- Addon names must use the program-approved prefix and stay consistent with the owning domain or capability.
- Model names, fields, security groups, menu items, scheduled actions, and XML IDs must be descriptive enough to trace back to an approved spec, data contract, or governance note.
- Cross-addon extension points must use names that reveal the dependency direction rather than obscure internal behavior.
- If a reviewer cannot identify the owning domain from the addon name and manifest, the naming contract is not satisfied.

## Control Block: Repository Change Decisions

- Add a new top-level directory only when an existing approved area cannot own the artifact without mixing responsibilities; the change requires architecture lead sign-off.
- Place new operational assets under `deployment/` when they affect runtime behavior, rollback, backup, monitoring, or service orchestration.
- Place migration-only helpers with the migration package or clearly named utility path, never inside unrelated business addons.
- Reject changes that scatter a single delivery concern across multiple top-level locations without a documented rationale.

## Evidence Required For Review Gates

| Gate or review area | Minimum evidence from this baseline |
| --- | --- |
| Gate 2: Blueprint Approved | Repository layout and addon policy acknowledged as the active structural baseline. |
| Gate 3: Domain Spec Approved | Domain spec identifies whether the scope maps to a new addon, existing addon, or OCA selection. |
| Gate 4: Build Approved | Addon manifest review, dependency rationale, boundary explanation, and install/upgrade/uninstall evidence. |
| Exception review | Written waiver showing which boundary rule is affected, why no safer structure exists, mitigation, owner, and expiry date. |

## Exception Path

- Structural exceptions are allowed only for temporary transition cases with a dated remediation plan.
- Exceptions cannot waive explicit dependency declarations, traceability, or install/uninstall safety.
- Every approved exception must name the affected repository area or addon, the risk owner, the cleanup trigger, and the gate where the exception will be re-evaluated.

## Review Cadence

- Review this baseline whenever a new domain introduces a custom addon, OCA selection, or repository structure change.
- Reconfirm applicability during Gate 3 and Gate 4 discussions for each domain slice.
- Update this document when a recurring structure or dependency decision becomes program policy.
