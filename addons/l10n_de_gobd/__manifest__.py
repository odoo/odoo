# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Germany - GOBD compliant accounting',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
This add-on brings the technical requirements for making German accounting
----------------------------------------------------------------------------

The module adds following features:

    Inalterability: deactivation of all the ways to cancel or modify key data, invoices and journal entries

""",
    'depends': ['l10n_de'],
    'installable': True,
    'auto_install': True,
    'application': False,
    'data': [],
    'post_init_hook': '_setup_inalterability',
}
