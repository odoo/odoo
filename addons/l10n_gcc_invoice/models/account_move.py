# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, api


_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None

class AccountMove(models.Model):
    _inherit = 'account.move'

    narration = fields.Html(translate=True)

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.country_id in self.env.ref('base.gulf_cooperation_council').country_ids:
            return 'l10n_gcc_invoice.arabic_english_invoice'
        return super()._get_name_invoice_report()

    def _num2words(self, number, lang):
        if num2words is None:
            _logger.warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        return num2words(number, lang=lang).title()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_gcc_invoice_tax_amount = fields.Float(string='Tax Amount', compute='_compute_tax_amount', digits='Product Price')

    @api.depends('price_subtotal', 'price_total')
    def _compute_tax_amount(self):
        for record in self:
            record.l10n_gcc_invoice_tax_amount = record.price_total - record.price_subtotal
