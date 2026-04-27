# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import get_timedelta

class SaleOrderTemplate(models.Model):
    _name = "sale.order.template"
    _inherit = 'sale.order.template'

    is_subscription = fields.Boolean(compute='_compute_is_subscription', search='_search_is_subscription')
    plan_id = fields.Many2one('sale.subscription.plan', string='Recurring Plan')

    # Duration, user duration property for access to the timedelta
    is_unlimited = fields.Boolean('Last Forever', default=True) # old recurring_rule_boundary
    duration_value = fields.Integer(string="End After", default=1, required=True) # old recurring_rule_count
    duration_unit = fields.Selection([('month', 'Months'), ('year', 'Years')], help="Contract duration", default='month', required=True) # old duration_unit

    _sql_constraints = [
        ('check_duration_value', 'CHECK(is_unlimited OR duration_value > 0)', 'The duration can\'t be negative or 0.'),
    ]

    @property
    def duration(self):
        if not self.duration_unit or not self.duration_value:
            return False
        return get_timedelta(self.duration_value, self.duration_unit)

    @api.depends('plan_id')
    def _compute_is_subscription(self):
        for template in self:
            template.is_subscription = bool(template.plan_id)

    @api.model
    def _search_is_subscription(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = [('plan_id', '!=', False)]
        else:
            domain = [('plan_id', '=', False)]
        return domain


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _inherit = 'sale.order.template.line'

    recurring_invoice = fields.Boolean(related='product_id.recurring_invoice')

class SaleOrderTemplateOption(models.Model):
    _name = "sale.order.template.option"
    _inherit = ['sale.order.template.option']

    recurring_invoice = fields.Boolean(related='product_id.recurring_invoice')
