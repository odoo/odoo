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

from osv import osv
import tools

class base_setup_company(osv.osv_memory):
    """
    """
    _name = 'base.setup.company'
    _inherit = 'res.config'

    def execute(self, cr, uid, ids, context=None):
        ir_pool = self.pool.get('ir.model.data')
        model, company_view_form = ir_pool.get_object_reference(cr, uid, 'base', 'view_company_form')
        model, company_view_tree = ir_pool.get_object_reference(cr, uid, 'base', 'view_company_tree')
        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        return {
            'name': _('Configure Company'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'crm.lead',
            'domain': [('id', '=', company_id)],
            'res_id': company_id,
            'view_id': False,
            'views': [(company_view_form, 'form'),
                      (company_view_tree, 'tree')],
            'type': 'ir.actions.act_window'
        }

base_setup_company()

class res_currency(osv.osv):
    _inherit = 'res.currency'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
#        We can use the following line,if we want to restrict this name_get for company setup only
#        But, its better to show currencies as name(Code).
        if not len(ids):
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','symbol'], context, load='_classic_write')
        return [(x['id'], tools.ustr(x['name']) + (x['symbol'] and (' (' + tools.ustr(x['symbol']) + ')') or '')) for x in reads]

res_currency()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
