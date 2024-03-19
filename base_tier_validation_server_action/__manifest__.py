# Copyright 2017-19 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Base Tier Validation - Server Action",
    "summary": "Add option to call server action when a tier is validated",
    "version": "17.0.0.0.0",
    "category": "Tools",
    "website": "https://github.com/OCA/server-ux",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["base_tier_validation"],
    "data": [
        "data/cron_data.xml",
        "views/tier_definition_view.xml",
    ],
    "maintainers": ["kittiu"],
    "development_status": "Beta",
}
