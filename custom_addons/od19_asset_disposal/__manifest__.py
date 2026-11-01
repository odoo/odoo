{
    "name": "Asset Disposal Workflow",
    "version": "19.0.1.0.0",
    "category": "Accounting & Finance",
    "summary": "Asset disposal workflow on top of account_asset_management",
    "description": """
Asset Disposal Workflow
=======================
Provides a disposal workflow for assets managed with OCA account_asset_management:

- Dispose asset: cancel draft depreciation moves, create a disposal journal
  entry (debit accumulated depreciation, credit asset cost, debit asset
  disposal account), set asset state to *disposed*.
- Revert disposal: reverse the disposal journal entry and set the asset back
  to *Running*.
- Linked documents: additional bills and supporting moves.
- Safe depreciation cron that computes depreciation per asset inside a
  savepoint, logging errors without aborting the whole job.
""",
    "author": "OD19",
    "website": "https://github.com/odoo/odoo",
    "license": "LGPL-3",
    "depends": [
        "account_asset_management",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/account_asset_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_asset_disposal/static/description/icon.svg",
}
