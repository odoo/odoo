# Copyright (C) 2013 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Point Of Sale - Change Payments",
    "version": "16.0.1.0.4",
    "summary": "Allow cashier to change order payments, as long as"
    " the session is not closed.",
    "category": "Point Of Sale",
    "author": "GRAP, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/pos",
    "license": "AGPL-3",
    "depends": ["point_of_sale"],
    "maintainers": ["legalsylvain"],
    "development_status": "Beta",
    "data": [
        "security/ir.model.access.csv",
        "wizards/view_pos_payment_change_wizard.xml",
        "views/view_pos_config.xml",
        "views/view_pos_order.xml",
    ],
    "installable": True,
}
