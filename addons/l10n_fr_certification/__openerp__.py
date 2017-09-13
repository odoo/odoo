# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Accounting - Certified CGI 286 I-3 bis',
    'version': '1.0',
    'category': 'Localization',
    'description': """This application allows to be in appliance with the inalterability, securisation and archiving of B2C sales entries, as required by the French Law (CGI art. 286, I. 3°bis) as of January 1st 2018.

        Don't uninstall this application. This would remove the inalterability check from previous sales entries.

        To be fully compliant with the law, this module goes with a certification provided by Odoo and downloadable here:
        https://accounts.odoo.com/my/contract/certification-comptabilite-francaise/

""",
    'depends': ['l10n_fr'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'data': [
        'views/no_cancel.xml',
        'data/account_move.xml',
    ],
    'post_init_hook': '_setup_inalterability',
}
