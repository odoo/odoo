# Copyright 2015 ABF OSIELL <https://osiell.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Audit Log",
    "version": "16.0.2.0.1",
    "author": "ABF OSIELL, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/server-tools",
    "category": "Tools",
    "depends": ["base"],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/auditlog_view.xml",
        "views/http_session_view.xml",
        "views/http_request_view.xml",
    ],
    "application": True,
    "installable": True,
}
