# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo import _, fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_down_payment_product(self):
        return self.env.ref('pos_sale.default_downpayment_product', raise_if_not_found=False)

    def _get_default_sol_product(self):
        return self.env.ref('pos_sale.default_sol_product', raise_if_not_found=False)

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", ondelete="set null", index='btree_not_null',
        help="This Point of sale's sales will be related to this Sales Team.")
    down_payment_product_id = fields.Many2one('product.product',
        string="Down Payment Product",
        default=_get_default_down_payment_product,
        help="This product will be used as down payment on a sale order.")
    default_product_id = fields.Many2one(
        'product.product',
        string="Default Product",
        default=_get_default_sol_product,
        help="This product will be used as default product on productless SOLs."
    )

    def _get_special_products(self):
        res = super()._get_special_products()
        return res | self.env['pos.config'].search([]).mapped(
            lambda config: config.down_payment_product_id | config.default_product_id
        )

    @api.model
    def _ensure_default_products(self):
        values = {}

        if downpayment_product := self._get_default_down_payment_product():
            values['down_payment_product_id'] = downpayment_product.id

        if default_sol_product := self._get_default_sol_product():
            values['default_product_id'] = default_sol_product.id

        if values:
            self.with_context(active_test=False).search([]).write(values)

    @api.constrains('default_product_id')
    def _check_default_products(self):
        for config in self:
            if not config.default_product_id:
                raise ValidationError(_("%s needs a Default Product", config.display_name))

    @api.constrains('down_payment_product_id')
    def _check_downproduct_products(self):
        for config in self:
            if not config.down_payment_product_id:
                raise ValidationError(_("%s needs a Down Payment Product", config.display_name))

    def _check_before_creating_new_session(self):
        if not (self.default_product_id and self.down_payment_product_id):
            self._ensure_default_products()
            if not self.default_product_id:
                raise UserError(_(
                    "Please set a Default Product on %s before opening a session.",
                    self.display_name,
                ))
            if not self.down_payment_product_id:
                raise UserError(_(
                    "Please set a Down Payment Product on %s before opening a session.",
                    self.display_name,
                ))
        return super()._check_before_creating_new_session()
