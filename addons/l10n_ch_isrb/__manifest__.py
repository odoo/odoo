# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Switzerland - ISR-B",
    'summary': "Switzerland - ISR with Bank",

    'description': """
    This patches l10n_ch to add a field `l10n_ch_isrb_id_number on
    `res.partner.bank`.
    """,
    'version': '1.0',
    'author': 'Odoo S.A',
    'category': 'Localization',

    'depends': ['l10n_ch'],

    'data': [
        'views/res_partner_bank.xml',
    ],

    'demo': [
    ],

}
