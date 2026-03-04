# Kore - sale_subscription - Source Attribution

## Legal basis
Clean-room implementation of the Odoo Enterprise `sale_subscription`
public API specification. No source code was copied or adapted from
any OCA module. OCA repositories were used as architectural reference
only to understand domain patterns, model boundaries, and workflow
expectations.

## Reference material consulted
| OCA repo | Module | License | Used for |
|----------|--------|---------|----------|
| contract | subscription_oca | AGPL-3 | Model structure and lifecycle architecture reference |
| contract | contract | LGPL-3/AGPL-3 in workspace headers | Recurring date and invoice pipeline pattern reference |

## File attribution
| File | Classification | Notes |
|------|----------------|-------|
| models/__init__.py | kore-original | Local model registry |
| models/sale_subscription.py | kore-original - informed by OCA/contract/subscription_oca architecture | Core model, recurrence, invoice creation |
| models/sale_subscription_line.py | kore-original - informed by OCA/contract/subscription_oca architecture | Line monetary calculations |
| models/sale_subscription_stage.py | kore-original - informed by OCA/contract/subscription_oca architecture | Stage lifecycle model |
| models/sale_subscription_template.py | kore-original - informed by OCA/contract/subscription_oca architecture | Template defaults model |
| models/sale_subscription_close_reason.py | kore-original - informed by OCA/contract/subscription_oca architecture | Close reason model |
| models/sale_subscription_tag.py | kore-original - informed by OCA/contract/subscription_oca architecture | Tag model |
| models/res_partner.py | kore-original - informed by OCA/contract/subscription_oca architecture | Partner subscription counters/actions |
| models/sale_subscription_gov_bridge.py | kore-original | Kore integration bridge for lifecycle events |

## What was NOT used
- No code from `subscription_oca` was copied. Its AGPL-3 license is
  reference-only for this clean-room output.
- No verbatim code from `contract` was copied.
- `sale.subscription.log` was dropped from the implemented scope because
  it is not required by the declared Kore compatibility target in this build.

