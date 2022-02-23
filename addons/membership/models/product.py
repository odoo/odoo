# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Product(models.Model):
    _inherit = 'product.template'

    membership = fields.Boolean(help='Check if the product is eligible for membership.')
    membership_date_from = fields.Date(string='Membership Start Date',
        help='Date from which membership becomes active.')
    membership_date_to = fields.Date(string='Membership End Date',
        help='Date until which membership remains active.')

    _sql_constraints = [
        ('membership_date_greater', 'check(membership_date_to >= membership_date_from)', 'Error ! Ending Date cannot be set before Beginning Date.')
    ]

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if self._context.get('product') == 'membership_product':
            if view_type == 'form':
                view_id = self.env.ref('membership.membership_products_form').id
            else:
                view_id = self.env.ref('membership.membership_products_tree').id
        return super().get_view(view_id, view_type, **options)
