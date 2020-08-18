# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# @author Team Optesis <teamsid@optesis.com>
# Copyright (c) Optesis 2018 www.optesis.com
{
    'name': 'Syscohada révisé',
    'version': '2.0.1',
    'author': 'Optesis',
    'license': 'LGPL-3',
    'website': 'http://www.optesis.com',
    'category': 'Localization',
    'description': """
                    Ce module permet de gérer le nouveau plan compable SYSCOHADA Révisé.
                    Ce module permet de gérer le nouveau plan compable SYSCOHADA Révisé
                    applicable à partir du 1er janvier 2018 pour tous les pays faisant partie de l'espace OHADA.
                    **Credits:** cabinet d'expertise comptable www.kyriex.com.
                    """,
    'depends': ['account','account_accountant','account_reports'],
    'data': [
        'views/menu_view.xml',
        'data/account_chart_template_data.xml',
        'data/account_tax_data.xml',
        'data/account_financial_html_report_data.xml',
        'data/l10n_pcgo_chart_data.xml',
    ],

}
