# Odoo, Open Source Web Company Color
# Copyright (C) 2019 Alexandre Díaz <dev@redneboa.es>
#
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).#
{
    "name": "Web Company Color",
    "category": "web",
    "version": "16.0.1.2.0",
    "author": "Alexandre Díaz, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "depends": ["web", "base_sparse_field"],
    "data": ["view/assets.xml", "view/res_company.xml"],
    "uninstall_hook": "uninstall_hook",
    "post_init_hook": "post_init_hook",
    "license": "AGPL-3",
    "auto_install": False,
    "installable": True,
}
