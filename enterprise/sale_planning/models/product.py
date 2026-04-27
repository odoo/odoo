# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    planning_enabled = fields.Boolean(
        'Plan Services',
        help="""If enabled, a shift will automatically be generated for the selected role when confirming the Sales Order. \
                With the 'auto plan' feature, only employees with this role will be automatically assigned shifts for Sales Orders containing this service. \
                The system will consider employee availability and the remaining time to be planned. \
                You can also manually schedule open shifts for your Sales Order or assign them to any employee you prefer.""",
    )
    planning_role_id = fields.Many2one('planning.role')

    @api.constrains('planning_enabled', 'uom_id')
    def _check_planning_product_uom_is_time(self):
        time_uom_category = self.env.ref('uom.uom_categ_wtime')
        unit_uom = self.env.ref('uom.product_uom_unit')
        if self.filtered(lambda product: product.planning_enabled and product.uom_id.category_id != time_uom_category and product.uom_id != unit_uom):
            raise ValidationError(_("Plannable services should use an UoM within the %s category.", time_uom_category.name))

    @api.constrains('planning_enabled', 'type')
    def _check_planning_product_is_service(self):
        invalid_products = self.filtered(lambda product: product.planning_enabled and product.type != 'service')
        if invalid_products:
            raise ValidationError(_("Plannable services should be a service product, product\n%s.", '\n'.join(invalid_products.mapped('name'))))
