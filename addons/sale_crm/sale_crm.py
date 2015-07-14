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

from openerp.osv import osv, fields

class res_users(osv.Model):
    _inherit = 'res.users'
    _columns = {
        'default_section_id': fields.many2one('crm.case.section', 'Default Sales Team'),
    }

    def __init__(self, pool, cr):
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['default_section_id'])
        return init_res

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]", context="{'object_name': 'crm.lead'}")
    }

    def _get_default_section_id(self, cr, uid, context=None):
        """ Gives default section by checking if present in the context """
        section_id = self.pool.get('crm.lead')._resolve_section_id_from_context(cr, uid, context=context) or False
        if not section_id:
            section_id = self.pool.get('res.users').browse(cr, uid, uid, context).default_section_id.id or False
        return section_id

    _defaults = {
        'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
    }

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        invoice_vals = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        if order.section_id and order.section_id.id:
            invoice_vals['section_id'] = order.section_id.id
        return invoice_vals


class sale_advance_payment_inv(osv.osv_memory):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_advance_invoice_vals(self, cr, uid, ids, context=None):
        result = super(sale_advance_payment_inv, self)._prepare_advance_invoice_vals(cr, uid, ids, context=context)
        orders = dict((order.id, order) for order in self.pool['sale.order'].browse(cr, uid, [order_id for order_id, values in result], context=context))
        for order_id, values in result:
            if orders.get(order_id) and orders[order_id].section_id:
                values['section_id'] = orders[order_id].section_id.id
        return result


class sale_order_line_make_invoice(osv.osv_memory):
    _inherit = "sale.order.line.make.invoice"

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        result = super(sale_order_line_make_invoice, self)._prepare_invoice(cr, uid, order, lines, context=context)
        if order.section_id:
            result['section_id'] = order.section_id.id
        return result


class sale_crm_lead(osv.Model):
    _inherit = 'crm.lead'

    def on_change_user(self, cr, uid, ids, user_id, context=None):
        """ Override of on change user_id on lead/opportunity; when having sale
            the new logic is :
            - use user.default_section_id
            - or fallback on previous behavior """
        if user_id:
            user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
            if user.default_section_id and user.default_section_id.id:
                return {'value': {'section_id': user.default_section_id.id}}
        return super(sale_crm_lead, self).on_change_user(cr, uid, ids, user_id, context=context)


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
    _defaults = {
        'section_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).default_section_id.id or False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
