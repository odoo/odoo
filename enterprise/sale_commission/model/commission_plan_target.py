# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class CommissionPlanTarget(models.Model):
    _name = 'sale.commission.plan.target'
    _description = 'Commission Plan Target'
    _order = 'id'

    plan_id = fields.Many2one('sale.commission.plan', ondelete='cascade')
    name = fields.Char("Period", required=True, readonly=True)
    date_from = fields.Date("From", required=True, readonly=True)
    date_to = fields.Date("To", required=True, readonly=True)
    amount = fields.Monetary("Target", default=0, required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='plan_id.currency_id')
