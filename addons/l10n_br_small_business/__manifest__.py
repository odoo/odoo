# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Brazilian - Plano de Contas Simplificado',
    'category': 'Localization',
    'description': """

Plano de Contas Simplificado do Conselho Federal de Contabilidade
=================================================================


""",
    'author': 'Odoo Brasil',
    'website': 'http://www.odoobrasil.org.br',
    'depends': [
        'l10n_br'
    ],
    'data': [
        'data/inherited_account_chart_template_data.xml',
        'data/inherited_account_chart_template_data.xml',
        'data/inherited_account_account_template_data.xml',
        'data/inherited_account_chart_template_properties_data.xml',
        "data/account_chart_template_data.yml",
    ],
    'installable': True,
}
