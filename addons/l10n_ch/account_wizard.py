# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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
import tools
from osv import  osv
import addons
import os

class WizardMultiChartsAccounts(osv.osv_memory):

    _inherit ='wizard.multi.charts.accounts'
    _defaults = {
        'bank_accounts_id': False,
        'code_digits': 0,
        'sale_tax': False,
        'purchase_tax':False
    }
 
    def execute(self, cr, uid, ids, context=None):
        """Override of code in order to be able to link journal with account in XML"""
        res = super(WizardMultiChartsAccounts, self).execute(cr, uid, ids, context)
        path = addons.get_module_resource(os.path.join('l10n_ch','sterchi_chart','account_journal_rel.xml'))
        tools.convert_xml_import(cr, 'l10n_ch', path, idref=None, mode='init', noupdate=True, report=None)
        return res
        
WizardMultiChartsAccounts()   

