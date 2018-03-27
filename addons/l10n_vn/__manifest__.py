# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    "name": "Vietnam - Accounting",
    "summary": "Vietnam Chart of Accounts for Odoo",
    "version": "2.0",
    "author": "General Solutions, Trobz, T.V.T Marine Automation (aka TVTMA)",
    'website': 'http://gscom.vn, https://ma.tvtmarine.com',
    'category': 'Localization',
    "description": """
With the new development, the module is now:
--------------------------------------------
* fully in compliance with the Circular #200/2014/TT-BTC dated Dec 22, 2014 by the Ministry of Finance which came into force on Jan 1, 2015
* partially in compliance with the Circular #133/2016/TT-BTC dated Aug 26, 2016 by the Ministry of Finance which came into force on Jan 1, 2017.

The following has been done and integrated
------------------------------------------
* More common taxes (e.g. import, export, special consumption, nature resource usage, etc)
* Complete Chart of Accounts
* Add one more field named code to the model account.account.tag so that Vietnamese accountants can use it the way of parent view account (like what was before Odoo 9). This bring peace to the accountants.
* New account tags data has been added to use in the similar way of parent view accounts before Odoo 9. For example, accountant now can group all accounts 111xxx using account the tag 111.
* Accounts now link to the tags having corresponding code. E.g. account 1111 and 1112 .... 111x have the same account tag of 111.
* According to Vietnam law, sale and purchase journals must have a dedicated sequence for any refund.
* Use English instead of Vietnamese to bring ease for worldwide developers and foreigners doing business in Vietnam. Translations for Vietnamese will be loaded upon loading Vietnamese and then installation of l10n_multilang module

Known issues
-------------
* There are a few accounts conflicts between those two circular (e.g. 3385, 3386, etc) which can be handled manually in the meantime. Future development should allow admin to select an appropriate COA (either c200 or c133)

Credits
-------
* General Solutions.
* Trobz
* ERPOnline
""",
    "depends": [
        "account",
        "base_iban",
        "l10n_multilang",
    ],
    "data": [
         'data/res.country.state.csv',
         'data/l10n_vn_chart_data.xml',
         'data/account_group_data.xml',
         'data/account.account.template.csv',
         'data/l10n_vn_chart_post_data.xml',
         'data/account_data.xml',
         'data/account_tax_report_data.xml',
         'data/account_tax_data.xml',
         'data/account_chart_template_data.xml',
    ],
    'post_init_hook': 'post_init',
}
