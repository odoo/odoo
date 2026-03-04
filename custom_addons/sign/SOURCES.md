# Kore - sign - Source Attribution

## Legal basis
This module is a clean-room implementation for Kore Odoo 19 CE.
All output is kore-original. No source code was copied or adapted.
References were used only for architectural orientation and coverage.

## Reference material consulted
| Source | Module / Scope | License | Usage classification |
|--------|-----------------|---------|----------------------|
| `sign\sign_oca` | `sign_oca` | AGPL-3 | Reference-only architecture signals for model boundaries and workflow coverage |
| Odoo Enterprise knowledge | `sign` public API contract | Proprietary | Public API behavior target for compatibility map |
| `automation\automation_oca` | automation patterns | AGPL-3 | Checked for sign hooks; no direct `sign.*` model hooks reused |

## File attribution
| File | Classification |
|------|----------------|
| `__manifest__.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_request.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_request_item.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_template.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_item.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_item_type.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_log.py` | kore-original — informed by `sign/sign_oca` architecture |
| `models/sign_gov_bridge.py` | kore-original — informed by Kore integration architecture |
| `wizard/sign_send_request_wizard.py` | kore-original — informed by Odoo wizard architecture |
| `security/sign_groups.xml` | kore-original — informed by Kore privilege model architecture |
| `security/sign_rules.xml` | kore-original — informed by Odoo record rule architecture |
| `security/ir.model.access.csv` | kore-original — informed by Odoo ACL architecture |
| `data/sign_item_type_data.xml` | kore-original — informed by Enterprise sign feature taxonomy |
| `data/sign_sequence.xml` | kore-original — informed by Odoo sequence architecture |
| `data/sign_cron.xml` | kore-original — informed by Odoo cron architecture |
| `views/*.xml` | kore-original — informed by Odoo view architecture |

## Method attribution
Every implemented public method below is classified:
`kore-original — informed by sign/sign_oca architecture`

| Method | Classification |
|--------|----------------|
| `sign.request.action_draft` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.action_sent` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.action_signed` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.action_refused` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.action_cancel` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request._send_signature_request_mail` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request._get_final_document` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request._compute_progress` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.send_reminder` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.item.action_draft` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.item.action_sent` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.item.action_completed` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.item.action_refused` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request.item._get_sign_link` | kore-original — informed by `sign/sign_oca` architecture |
| `sign.request._get_signing_event_type` | kore-original — informed by Kore lifecycle architecture |

## Explicit exclusions
- No verbatim, converted, or adapted code from `sign_oca`.
- No code reuse from `project_task_sign_oca`.
- No code reuse from `automation_oca`.

