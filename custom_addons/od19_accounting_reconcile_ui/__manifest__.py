# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Accounting Reconcile UI (OCA bridge)",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Accounting/Localizations",
    "summary": "Bridge linking the OD19 accounting core with the OCA manual "
    "reconciliation UI (account_reconcile_oca). Auto-installs when both "
    "sides are present, so the OD19 core no longer hard-depends on OCA.",
    "description": """
OD19 Accounting Reconcile UI (OCA bridge)
=========================================

This is a *bridge* module: it carries no business logic of its own. Its only
purpose is to keep the OD19 accounting core (``od19_accounting_features``)
decoupled from the OCA manual reconciliation UI (``account_reconcile_oca``).

Why a bridge?
-------------

* ``account_reconcile_oca`` is licensed AGPL-3 and is an external,
  community-maintained addon. Keeping it out of the hard dependency list of
  the OD19 core means the core can be deployed, reused or moved (e.g. on
  Odoo Enterprise, which ships its own reconciliation widget) without pulling
  the OCA addon in.
* ``auto_install`` is ``True`` so this bridge is installed *automatically* as
  soon as **both** dependencies are already installed. A normal OD19 CE
  deployment therefore still gets the OCA reconcile UI with a single
  ``-i od19_accounting_reconcile_ui`` (or ``STEP-2 -All``) step.

What the OCA UI adds
--------------------

The Thai period-clearing wizard and the central reconciliation helpers live
in ``od19_accounting_features`` and work independently of this bridge. The
OCA addon only provides the manual matching screen (menu
``Accounting ▸ Accounting ▸ Reconcile``) for the remaining open items, plus
the "Reconcile" contextual action on accounts and partners.

Installation note
-----------------

Because the OD19 core no longer depends on the OCA addon, a fresh database
created with ``-i od19_accounting_features`` alone will *not* pull the OCA
UI in. Install this bridge explicitly (which pulls both dependencies) or run
``STEP-2-Install-Odoo19.ps1 -All``.
    """,
    "depends": [
        "od19_accounting_features",
        "account_reconcile_oca",
    ],
    "auto_install": True,
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_accounting_reconcile_ui/static/description/icon.svg",
}
