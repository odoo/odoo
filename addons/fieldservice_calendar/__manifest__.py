# Copyright (C) 2021 Raphaël Reverdy <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Field Service - Calendar",
    "summary": "Add calendar to FSM Orders",
    "author": "Akretion, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/field-service",
    "category": "Field Service",
    "license": "AGPL-3",
    "version": "18.0.1.0.0",
    "depends": [
        "calendar",
        "fieldservice",
    ],
    "data": [
        "views/fsm_order.xml",
        "views/fsm_team.xml",
    ],
    "installable": True,
    "development_status": "Beta",
    "maintainers": [
        "hparfr",
    ],
}
