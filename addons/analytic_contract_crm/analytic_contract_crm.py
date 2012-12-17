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
        manager_id = self.browse(cr, uid, obj_id, context=context).manager_id
        if manager_id:
            if manager_id.default_section_id:
                # subscribe salesteam followers & subtypes to the contract
                self._subscribe_followers_subtype(cr, uid, [obj_id], manager_id.default_section_id, 'crm.case.section', context=context)
        if obj_id:
            self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('manager_id'):
            section_id = self.pool.get('res.users').browse(cr, uid, vals.get('manager_id'), context=context).default_section_id
            if section_id:
                vals.setdefault('message_follower_ids', [])
                vals['message_follower_ids'] += [(6, 0,[follower.id]) for follower in section_id.message_follower_ids]
        res = super(account_analytic_account, self).write(cr, uid, ids, vals, context=context)
        # subscribe new salesteam followers & subtypes to the contract
        if vals.get('manager_id'):
            if section_id:
                self._subscribe_followers_subtype(cr, uid, ids, section_id, 'crm.case.section', context=context)
        return res 

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
