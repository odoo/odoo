# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'EU One Stop Shop (OSS)',
    'category': 'Accounting/Localizations',
    'description': """
EU One Stop Shop (OSS) VAT
==========================

From July 1st 2021, EU businesses that are selling goods within the EU above EUR 10 000 to buyers located in another EU Member State need to register and pay VAT in the buyers’ Member State.
Below this new EU-wide threshold you can continue to apply the domestic rules for VAT on your cross-border sales. In order to simplify the application of this EU directive, the One Stop Shop (OSS) registration scheme allows businesses to make a unique tax declaration.

This module makes it possible by helping with the creation of the required EU fiscal positions and taxes in order to automatically apply and record the required taxes.

All you have to do is check that the proposed mapping is suitable for the products and services you sell.

References
++++++++++
Council Directive (EU) 2017/2455 Council Directive (EU) 2019/1995
Council Implementing Regulation (EU) 2019/2026

    """,
    'depends': ['account'],
    'data': [
        'views/res_config_settings_views.xml',
        'data/account_account_tag.xml',
    ],
    'uninstall_hook': 'l10n_eu_oss_uninstall',
    'license': 'LGPL-3',
}
