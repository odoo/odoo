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

class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"

    def create(self, cr, uid, vals, context=None):
        obj_id =  super(account_analytic_account, self).create(cr, uid, vals, context=context)
        self._subscribe_salesteam_followers_to_contract(cr, uid, [obj_id], context)
        if obj_id:
            self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(account_analytic_account, self).write(cr, uid, ids, vals, context=context)
        if vals.get('partner_id'):
            self._subscribe_salesteam_followers_to_contract(cr, uid, ids, context)
        return res 

    def _subscribe_salesteam_followers_to_contract(self, cr, uid, obj_id, context=None):
        follower_obj = self.pool.get('mail.followers')
        subtype_obj = self.pool.get('mail.message.subtype')
        record = self.browse(cr, uid, obj_id, context=context)[0]
        if record.partner_id:
            if record.partner_id.section_id:
                followers = [follow.id for follow in record.partner_id.section_id.message_follower_ids]
                contract_subtype_ids = subtype_obj.search(cr, uid, ['|', ('res_model', '=', False), ('res_model', '=', self._name)], context=context)
                contract_subtypes = subtype_obj.browse(cr, uid, contract_subtype_ids, context=context)
                follower_ids = follower_obj.search(cr, uid, [('res_model', '=', 'crm.case.section'), ('res_id', '=', record.partner_id.section_id.id)], context=context)
                self.write(cr, uid, obj_id, {'message_follower_ids': [(6, 0, followers)]}, context=context)
                for follower in follower_obj.browse(cr, uid, follower_ids, context=context):
                    if not follower.subtype_ids:
                        continue
                    salesteam_subtype_names = [salesteam_subtype.name for salesteam_subtype in follower.subtype_ids]
                    contract_subtype_ids = [contract_subtype.id for contract_subtype in contract_subtypes if contract_subtype.name in salesteam_subtype_names]
                    self.message_subscribe(cr, uid, obj_id, [follower.partner_id.id], subtype_ids=contract_subtype_ids, context=context)
        else:
            return

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
