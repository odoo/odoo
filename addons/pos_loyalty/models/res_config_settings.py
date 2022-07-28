# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_loyalty_program_id = fields.Many2one('loyalty.program', compute='_compute_pos_loyalty_id', store=True, readonly=False)

    pos_use_coupon_programs = fields.Boolean(related='pos_config_id.use_coupon_programs', readonly=False)
    pos_coupon_program_ids = fields.Many2many(related='pos_config_id.coupon_program_ids', readonly=False)
    pos_promo_program_ids = fields.Many2many(related='pos_config_id.promo_program_ids', readonly=False)

    pos_use_gift_card = fields.Boolean(related='pos_config_id.use_gift_card', readonly=False, string="Gift Cards (PoS)")
    pos_gift_card_program_id = fields.Many2one(related='pos_config_id.gift_card_program_id', readonly=False)
    pos_gift_card_settings = fields.Selection(related='pos_config_id.gift_card_settings', readonly=False)

    @api.depends('pos_module_pos_loyalty', 'pos_config_id')
    def _compute_pos_loyalty_id(self):
        for res_config in self:
            if res_config.pos_module_pos_loyalty:
                res_config.pos_loyalty_program_id = res_config.pos_config_id.loyalty_program_id or res_config.pos_config_id._default_loyalty_program()
            else:
                res_config.pos_loyalty_program_id = False
