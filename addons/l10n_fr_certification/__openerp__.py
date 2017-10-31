# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Certification CGI 286 I-3 bis',
    'version': '1.0',
    'category': 'Localization',
    'description': """This application allows to be in appliance with the inalterability, securisation and archiving of journal entries, as required by the French Law (CGI art. 286, I. 3°bis) as of January 1st 2018.

        Don't uninstall this application. This would remove the inalterability check on existing previous journal entries.

        To be fully compliant with the law, this module goes with a certification provided by Odoo that is downloadable here:
        https://accounts.odoo.com/my/contract/certification-french-accounting/

""",
    'depends': ['l10n_fr'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'data': [
        'data/account_move.xml',
        'views/res_config.xml',
        'views/account_sale_closure.xml'
    ],
    'post_init_hook': '_setup_inalterability',
}
