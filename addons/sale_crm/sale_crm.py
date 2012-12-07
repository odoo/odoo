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
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]")
    }

    def create(self, cr, uid, vals, context=None):
        order =  super(sale_order, self).create(cr, uid, vals, context=context)
        self._subscribe_salesteam_followers_to_order(cr, uid, order, context=context)
        return order

    def _subscribe_salesteam_followers_to_order(self, cr, uid, order, context=None):
        follower_obj = self.pool.get('mail.followers')
        subtype_obj = self.pool.get('mail.message.subtype')
        section_id = self.browse(cr, uid, order, context=context).section_id
        if section_id:
            followers = [follow.id for follow in section_id.message_follower_ids]
            order_subtype_ids = subtype_obj.search(cr, uid, ['|', ('res_model', '=', False), ('res_model', '=', self._name)], context=context)
            order_subtypes = subtype_obj.browse(cr, uid, order_subtype_ids, context=context)
            followers = [follow.id for follow in section_id.message_follower_ids]
            follower_ids = follower_obj.search(cr, uid, [('res_model', '=', 'crm.case.section'), ('res_id', '=', section_id)], context=context)
            self.write(cr, uid, order, {'message_follower_ids': [(6, 0, followers)]}, context=context)
            for follower in follower_obj.browse(cr, uid, follower_ids, context=context):
                if not follower.subtype_ids:
                    continue
                salesteam_subtype_names = [salesteam_subtype.name for salesteam_subtype in follower.subtype_ids]
                order_subtype_ids = [order_subtype.id for order_subtype in order_subtypes if order_subtype.name in salesteam_subtype_names]
                self.message_subscribe(cr, uid, [order], [follower.partner_id.id], subtype_ids=order_subtype_ids, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        res = super(sale_order, self).write(cr, uid, ids, vals, context=context)
        if vals.get('section_id'):
            for id in ids:
                self._subscribe_salesteam_followers_to_order(cr, uid, id, context=context)
        return res

sale_order()

class res_users(osv.Model):
    _inherit = 'res.users'
    _columns = {
        'default_section_id': fields.many2one('crm.case.section', 'Default Sales Team'),
    }

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
    _defaults = {
        'section_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).default_section_id.id or False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
