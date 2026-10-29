# Copyright 2014 ABF OSIELL <http://osiell.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


{
    "name": "User roles",
    "version": "16.0.1.4.1",
    "category": "Tools",
    "author": "ABF OSIELL, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "development_status": "Production/Stable",
    "maintainers": ["sebalix", "jcdrubay", "novawish"],
    "website": "https://github.com/OCA/server-backend",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "data/ir_module_category.xml",
        "views/role.xml",
        "views/user.xml",
        "views/group.xml",
        "wizards/create_from_user.xml",
        "wizards/wizard_groups_into_role.xml",
    ],
    "installable": True,
}
