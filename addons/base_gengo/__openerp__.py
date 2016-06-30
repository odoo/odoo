# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Automated Translations through Gengo API',
    'version': '0.1',
    'category': 'Extra Tools',
    'description': """
Automated Translations through Gengo API
========================================

This module will install passive scheduler job for automated translations 
using the Gengo API. To activate it, you must
1) Configure your Gengo authentication parameters under `Settings > Companies > Gengo Parameters`
2) Launch the wizard under `Settings > Application Terms > Gengo: Manual Request of Translation` and follow the wizard.

This wizard will activate the CRON job and the Scheduler and will start the automatic translation via Gengo Services for all the terms where you requested it.
    """,
    'depends': ['base'],
    'data': [
        'gengo_sync_schedular_data.xml',
        'ir_translation.xml',
        'res_company_view.xml',
        'wizard/base_gengo_translations_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
