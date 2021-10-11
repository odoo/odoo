# -*- coding: utf-8 -*-
"""
@author: Online ERP Hungary Kft.
"""

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _set_price_and_tax_after_fpos(self):
        self = self.with_context(l10n_hu_product_id=self.product_id)
        return super(AccountMoveLine, self)._set_price_and_tax_after_fpos()

    @api.onchange("product_id")
    def _onchange_product_id(self):
        self = self.with_context(l10n_hu_product_id=self.product_id)
        return super(AccountMoveLine, self)._onchange_product_id()

    def _get_computed_price_unit(self):
        self.ensure_one()
        self = self.with_context(l10n_hu_product_id=self.product_id)
        return super(AccountMoveLine, self)._get_computed_price_unit()

    @api.onchange("product_uom_id")
    def _onchange_uom_id(self):
        self = self.with_context(l10n_hu_product_id=self.product_id)
        return super(AccountMoveLine, self)._onchange_uom_id()
