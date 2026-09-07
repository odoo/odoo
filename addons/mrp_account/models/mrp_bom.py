from odoo import models, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    extra_cost = fields.Monetary(string='Extra Cost', currency_field='currency_id', default=0.0, store=True, readonly=False)
