# Copyright 2013 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    "name": "Connector",
    "version": "16.0.1.0.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/connector",
    "license": "LGPL-3",
    "category": "Generic Modules",
    "depends": ["mail", "queue_job", "component", "component_event"],
    "data": [
        "security/connector_security.xml",
        "views/connector_menu.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
}
