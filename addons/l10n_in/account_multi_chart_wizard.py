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
from osv import fields, osv
from os.path import join as opj

class account_multi_charts_wizard(osv.osv_memory):
    _inherit ='wizard.multi.charts.accounts'
    _columns = {
        'sales_tax': fields.boolean('Sales tax central'),     
        'vat': fields.boolean('VAT resellers'),
        'service_tax': fields.boolean('Service tax'),
        'excise_duty': fields.boolean('Excise duty'),
    }    

    def execute(self, cr, uid, ids, context=None):
        super(account_multi_charts_wizard, self).execute(cr, uid, ids, context)
        obj_multi = self.browse(cr, uid, ids[0])
        if obj_multi.chart_template_id.name == 'Public Firm Chart of Account':
            path = tools.file_open(opj('l10n_in', 'account_sale_tax.xml'))
            tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
            path.close()   
        elif obj_multi.chart_template_id.name == 'Partnership/Private Firm Chart of Account':
            path = tools.file_open(opj('l10n_in', 'account_vat.xml'))
            tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
            path.close() 
            

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
