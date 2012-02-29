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

class account_configuration(osv.osv_memory):
    _inherit = 'res.config'

    _columns = {
            'tax_policy': fields.selection([
                ('no_tax', 'No Tax'),
                ('global_on_order', 'Global On Order'),
                ('on_order_line', 'On Order Lines'),
            ], 'Taxes', required=True),
            'tax_value': fields.float('Value'),
    }
    
    _defaults = {
        'tax_policy': 'global_on_order',
        'tax_value': 15.0,
    }
    
    def get_tax_value(self, cr, uid, ids, context=None):
        result = {}
        chart_account_obj = self.pool.get('wizard.multi.charts.accounts')
        chart_account_obj.execute(cr, uid, ids, context=context)
        return result
    
account_configuration()