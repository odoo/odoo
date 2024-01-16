# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    narration = fields.Html(translate=True)

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.country_id in self.env.ref('base.gulf_cooperation_council').country_ids:
            return 'l10n_gcc_invoice.arabic_english_invoice'
        return super()._get_name_invoice_report()

    def _load_narration_translation(self):
        # Workaround to have the english/arabic version of the payment terms
        # in the report
        if not self:
            return
        gcc_countries = self.env.ref('base.gulf_cooperation_council').country_ids
        moves_to_fix = self.env['account.move']
        for move in self.filtered(lambda m: m.company_id.country_id in gcc_countries and m.is_sale_document(include_receipts=True) and m.narration):
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

    l10n_gcc_invoice_tax_amount = fields.Float(string='Tax Amount', compute='_compute_tax_amount', digits='Product Price')

    @api.depends('price_subtotal', 'price_total')
    def _compute_tax_amount(self):
        for record in self:
            record.l10n_gcc_invoice_tax_amount = record.price_total - record.price_subtotal
