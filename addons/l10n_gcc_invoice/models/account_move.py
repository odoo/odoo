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

    def _l10n_gcc_get_invoice_title(self):
        """To be overriden by inheriting modules implementing a custom invoice title"""
        self.ensure_one()
        return False

    def _num2words(self, number, lang):
        if num2words is None:
            _logger.warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        return num2words(number, lang=lang).title()

    def _load_narration_translation(self):
        # Workaround to have the english/arabic version of the payment terms
        # in the report
        if not self:
            return
        moves_to_fix = self.env['account.move']
        for move in self.filtered(lambda m: m.narration and m.is_sale_document(include_receipts=True) and m.company_id.country_id and 'GCC' in m.company_id.country_id.country_group_codes):
            lang = move.partner_id.lang or self.env.user.lang
            if move.company_id.terms_type == 'html' or move.narration != move.company_id.with_context(lang=lang).invoice_terms:
                continue
            moves_to_fix |= move
        if not moves_to_fix:
            return
        self.env['res.company'].flush_model(['invoice_terms'])
        self.env.cr.execute('SELECT "id","invoice_terms" FROM "res_company" WHERE id = any(%s)', [moves_to_fix.company_id.ids])
        translation_by_company_id = {company_id: narration for company_id, narration in self.env.cr.fetchall()}
        self.env.cache.update_raw(moves_to_fix, self._fields['narration'], [
            translation_by_company_id[move.company_id.id]
            for move in moves_to_fix
        ], dirty=True)
        moves_to_fix.modified(['narration'])

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._load_narration_translation()
        return moves

    def _compute_narration(self):
        super()._compute_narration()
        # Only update translations of real records
        self.filtered('id')._load_narration_translation()


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
