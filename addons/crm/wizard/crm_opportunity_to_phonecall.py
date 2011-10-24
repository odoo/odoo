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

from osv import osv, fields
from tools.translate import _
import pprint
pp = pprint.PrettyPrinter(indent=4)

import time

class crm_opportunity2phonecall(osv.osv_memory):
    """Converts Opportunity to Phonecall"""
    _inherit = 'crm.phonecall2phonecall'
    _name = 'crm.opportunity2phonecall'
    _description = 'Opportunity to Phonecall'

    def default_get(self, cr, uid, fields, context=None):
        opp_obj = self.pool.get('crm.lead')
        categ_id = False
        data_obj = self.pool.get('ir.model.data')
        res_id = data_obj._get_id(cr, uid, 'crm', 'categ_phone2')
        if res_id:
            categ_id = data_obj.browse(cr, uid, res_id, context=context).res_id

        record_ids = context and context.get('active_ids', []) or []
        res = super(crm_opportunity2phonecall, self).default_get(cr, uid, fields, context=context)
        res.update({'action': 'schedule', 'date': time.strftime('%Y-%m-%d %H:%M:%S')})
        for opp in opp_obj.browse(cr, uid, record_ids, context=context):
            if 'name' in fields:
                res.update({'name': opp.name})
            if 'user_id' in fields:
                res.update({'user_id': opp.user_id and opp.user_id.id or False})
            if 'section_id' in fields:
                res.update({'section_id': opp.section_id and opp.section_id.id or False})
            if 'categ_id' in fields:
                res.update({'categ_id': categ_id})
            if 'partner_id' in fields:
                res.update({'partner_id': opp.partner_id and opp.partner_id.id or False})
        return res

    def action_schedule(self, cr, uid, ids, context=None):
        value = {}
        if context is None:
            context = {}
        phonecall = self.pool.get('crm.phonecall')
        opportunity_ids = context and context.get('active_ids') or []
        opportunity = self.pool.get('crm.lead')
        data = self.browse(cr, uid, ids, context=context)[0]
        call_ids = opportunity.schedule_phonecall(cr, uid, opportunity_ids, data.date, data.name, \
                data.user_id and data.user_id.id or False, \
                data.section_id and data.section_id.id or False, \
                data.categ_id and data.categ_id.id or False, \
                action=data.action, context=context)
        return phonecall.redirect_phonecall_view(cr, uid, call_ids[opportunity_ids[0]], context=context)

crm_opportunity2phonecall()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
