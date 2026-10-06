# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

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
        if self.company_id.country_id and 'GCC' in self.company_id.country_id.country_group_codes:
            return 'l10n_gcc_invoice.l10n_gcc_report_invoice_document'
        return super()._get_name_invoice_report()

    def _num2words(self, number, lang):
        if num2words is None:
            _logger.warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        return num2words(number, lang=lang).title()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_gcc_invoice_tax_amount = fields.Float(string='Tax Amount', compute='_compute_tax_amount', min_display_digits='Product Price')
    l10n_gcc_line_name = fields.Char(compute='_compute_l10n_gcc_line_name')

    @api.depends('price_subtotal', 'price_total')
    def _compute_tax_amount(self):
        for record in self:
            record.l10n_gcc_invoice_tax_amount = record.price_total - record.price_subtotal

    @api.depends('name')
    def _compute_l10n_gcc_line_name(self):
        def lang_product_name(line, lang):
            return line.with_context(lang=lang).product_id.display_name
        for line in self:
            if line.product_id and line.name in [lang_product_name(line, lang) for lang in ('ar_001', 'en_US')]:
                line.l10n_gcc_line_name = lang_product_name(line, line.move_id.partner_id.lang)
            else:
                line.l10n_gcc_line_name = line.name

    def _get_child_lines(self):
        # EXTENDS account
        self.ensure_one()
        res = super()._get_child_lines()

        for line in res:
            line['l10n_gcc_invoice_tax_amount'] = line['price_total'] - line['price_subtotal']

        return res

    def _l10n_gcc_get_section_total(self):
        section_lines = self._get_section_lines()
        return sum(section_lines.mapped('price_total'))

    def _l10n_gcc_get_section_tax_amount(self):
        section_lines = self._get_section_lines()
        return sum(section_lines.mapped('l10n_gcc_invoice_tax_amount'))
