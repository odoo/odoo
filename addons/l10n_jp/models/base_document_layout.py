# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    l10n_jp_currency_in_headers = fields.Boolean(related='company_id.l10n_jp_currency_in_headers', readonly=False)
    l10n_jp_is_jp_layout = fields.Boolean(compute='_compute_l10n_jp_is_jp_layout')

    @api.depends('report_layout_id')
    def _compute_l10n_jp_is_jp_layout(self):
        jp_layout = self.env.ref('l10n_jp.report_layout_jp_standard', raise_if_not_found=False)
        for wizard in self:
            wizard.l10n_jp_is_jp_layout = bool(jp_layout) and wizard.report_layout_id == jp_layout

    @api.depends('l10n_jp_currency_in_headers')
    def _compute_preview(self):
        super()._compute_preview()

    @api.model
    def _extract_company_layout_vals(self, vals):
        company_vals = super()._extract_company_layout_vals(vals)
        if 'l10n_jp_currency_in_headers' in vals:
            company_vals['l10n_jp_currency_in_headers'] = vals.pop('l10n_jp_currency_in_headers')
        return company_vals
