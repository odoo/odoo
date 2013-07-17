# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Automated Translations through Gengo API',
    'version': '0.1',
    'category': 'Tools',
    'description': """
Automated Translations through Gengo API
========================================

This module will install passive scheduler job for automated translations 
using the Gengo API. To activate it, you must
1) Configure your Gengo authentication parameters under `Settings > Companies > Gengo Parameters`
2) Launch the wizard under `Settings > Application Terms > Gengo: Manual Request of Translation` and follow the wizard.

This wizard will activate the CRON job and the Scheduler and will start the automatic translation via Gengo Services for all the terms where you requested it.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': ['gengo_sync_schedular_data.xml'],
    'update_xml': [
        'ir_translation.xml',
        'res_company_view.xml',
        'wizard/base_gengo_translations_view.xml',
           ],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
