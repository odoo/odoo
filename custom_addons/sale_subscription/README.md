sale_subscription - Kore Tier 2 Substitute
==========================================

Purpose
-------

Kore clean-room implementation of the Odoo Enterprise sale_subscription
contract so modules that depend on sale_subscription resolve in Kore.

Build Basis
-----------

Clean-room implementation. No OCA code included. OCA repositories were
consulted as architectural reference only. See SOURCES.md.

Enterprise Contract Coverage
----------------------------

* Core models sale.subscription, line, stage, template, close.reason:
  implemented.
* Recurrence and invoice pipeline: implemented.
* Required XML IDs and actions: implemented.
* Security: implemented with ACL, company rules and privilege_id groups.
* Optional sale.subscription.log: intentionally dropped.

Known Gaps
----------

See GAPS.md. This build has no STUB items.

Integration
-----------

* gov suite lifecycle events exposed via _get_lifecycle_event_type for
  base_automation rules without hard dependency.
* om_account_accountant compatibility maintained by setting
  move_type out_invoice on generated invoices.
* qbo_online_mirror migration boundary documented above
  _recurring_create_invoice.

Conventions
-----------

* Version: 1.0.1.0.0.
* License: LGPL-3.
* Groups: privilege_id only.
* Frozen base: not modified.
