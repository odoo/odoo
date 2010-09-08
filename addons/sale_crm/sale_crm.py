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

from osv import osv,fields

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
    def action_cancel(self, cr, uid, ids, context=None):
        res = super(sale_order, self).action_cancel(cr, uid, ids, context=context)
        case_pool = self.pool.get('crm.lead')
        data_pool = self.pool.get('ir.model.data')
        data = data_pool._get_id(cr, uid, 'crm', 'stage_lead6')
        res_data = data_pool.read(cr, uid, data, ['res_id'])
        lost_stage_id = False
        if res_data and res_data.get('res_id'):
            lost_stage_id = res_data.get('res_id', False)
        if not lost_stage_id:
            return res
        # After sale cancel, lead also lost
        for sale_id in ids:
            lead_ids = case_pool.search(cr, uid, [('ref','=','sale.order,%s'%(sale_id))])
            case_pool.write(cr, uid, lead_ids, {'stage_id': lost_stage_id})
        return res
    def action_ship_create(self, cr, uid, ids, *args):
        res = super(sale_order, self).action_ship_create(cr, uid, ids, *args)
        case_pool = self.pool.get('crm.lead')
        data_pool = self.pool.get('ir.model.data')
        data = data_pool._get_id(cr, uid, 'crm', 'stage_lead5')
        res_data = data_pool.read(cr, uid, data, ['res_id'])
        win_stage_id = False
        if res_data and res_data.get('res_id'):
            win_stage_id = res_data.get('res_id', False)
        if not win_stage_id:
            return res
        # After sale confimed, lead also win
        for sale_id in ids:
            lead_ids = case_pool.search(cr, uid, [('ref','=','sale.order,%s'%(sale_id))])
            case_pool.write(cr, uid, lead_ids, {'stage_id': win_stage_id})
        return res
    def _get_section(self, cr, uid, context=None):
       return context.get('context_section_id', False)

    _defaults = {
          'section_id': _get_section
    }

sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
