# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _inherit = ['loyalty.rule', 'pos.load.mixin']

    promo_barcode = fields.Char(
        "Barcode",
        compute='_compute_promo_barcode',
        store=True,
        readonly=False,
        help="A technical field used as an alternative to the promo code. "
        "This is automatically generated when the promo code is changed.",
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('program_id', 'in', config.loyalty_program_ids.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['program_id', 'currency_id', 'product_ids', 'product_domain',
            'reward_point_amount', 'reward_point_split', 'reward_point_mode', 'product_category_id',
            'minimum_qty', 'minimum_amount', 'minimum_amount_tax_mode', 'mode', 'code']

    @api.depends('code')
    def _compute_promo_barcode(self):
        for rule in self:
            rule.promo_barcode = self.env['loyalty.card']._generate_code()
