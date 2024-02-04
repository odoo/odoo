# Copyright 2015 Francesco OpenCode Apruzzese <cescoap@gmail.com>
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2017 Thomas Binsfeld <thomas.binsfeld@acsone.eu>
# Copyright 2017 Xavier Jiménez <xavier.jimenez@qubiq.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Web Environment Ribbon",
    "version": "16.0.1.0.0",
    "category": "Web",
    "author": "Francesco OpenCode Apruzzese, "
    "Tecnativa, "
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "license": "AGPL-3",
    "depends": ["web"],
    "data": [
        "data/ribbon_data.xml",
    ],
    "auto_install": False,
    "installable": True,
    "assets": {
        "web.assets_common": [
            "web_environment_ribbon/static/**/*",
        ],
    },
}
