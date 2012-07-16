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

from osv import fields, osv
from os.path import join as opj
import tools

class l10n_installer(osv.osv_memory):
    _inherit = 'account.installer'
    _columns = {
        'company_type': fields.selection([('public_company', 'Public Ltd'),
                                         ('partnership_private_company', 'Private Ltd/Partnership')
                                         ], 'Company Type', required=True,
                                        help='Company Type is used to install Indian chart of accounts as per need of business.'),
    }
    _defaults = {
        'company_type': 'public_company',
    }
    
    def execute_simple(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        res = super(l10n_installer, self).execute_simple(cr, uid, ids, context=context)
        
        for chart in self.read(cr, uid, ids, context=context):

            if chart['charts'] =='l10n_in' and chart['company_type']=='public_company':
                acc_file_path = tools.file_open(opj('l10n_in', 'l10n_in_public_chart.xml'))

                tools.convert_xml_import(cr, 'l10n_in', acc_file_path, {}, 'init', True, None)
                acc_file_path.close() 
                
                tax_file_path = tools.file_open(opj('l10n_in', 'l10n_in_public_tax_template.xml'))
                tools.convert_xml_import(cr, 'l10n_in', tax_file_path, {}, 'init', True, None)
                tax_file_path.close()  

            elif chart['charts'] =='l10n_in' and chart['company_type']=='partnership_private_company':
                acc_file_path = tools.file_open(opj('l10n_in', 'l10n_in_private_chart.xml'))

                tools.convert_xml_import(cr, 'l10n_in', acc_file_path, {}, 'init', True, None)
                acc_file_path.close()  

                tax_file_path = tools.file_open(opj('l10n_in', 'l10n_in_private_tax_template.xml'))
                tools.convert_xml_import(cr, 'l10n_in', tax_file_path, {}, 'init', True, None)
                tax_file_path.close()        
                        
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: