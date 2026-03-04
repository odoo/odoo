Sign (Kore Tier 2)
==================

Kore clean-room substitute for document signature workflows.

Delivered Scope
---------------

* Request lifecycle draft, sent, signed, refused, canceled and expired.
* Signers with secure tokenized links.
* Template management with positioned sign items.
* Email dispatch for signature requests and reminders.
* Reminder cron.
* Kore integration bridge:
  optional subscription activation hook on signature completion and
  lifecycle key provider for automation.

Security
--------

* Privilege model via res.groups.privilege and res.groups with privilege_id.
* Company scoping rules on sign.request.
* Public and portal access restricted by sign.request.item partner rule.

Notes
-----

sign.request._get_final_document remains intentionally stubbed.
See GAPS.md for details.
