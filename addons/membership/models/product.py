# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class Product(osv.osv):
    _inherit = 'product.template'

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        ModelData = self.pool['ir.model.data']
        if context is None:
            context = {}

        if ('product' in context) and (context['product']=='membership_product'):
            if view_type == 'form':
                view_id = ModelData.xmlid_to_res_id(
                    cr, user, 'membership.membership_products_form', context=context)
            else:
                view_id = ModelData.xmlid_to_res_id(
                    cr, user, 'membership.membership_products_tree', context=context)
        return super(Product,self).fields_view_get(cr, user, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

    _columns = {
        'membership': fields.boolean('Membership', help='Check if the product is eligible for membership.'),
        'membership_date_from': fields.date('Membership Start Date', help='Date from which membership becomes active.'),
        'membership_date_to': fields.date('Membership End Date', help='Date until which membership remains active.'),
    }

    _sql_constraints = [('membership_date_greater','check(membership_date_to >= membership_date_from)','Error ! Ending Date cannot be set before Beginning Date.')]
