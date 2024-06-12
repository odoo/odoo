from odoo import models, fields

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    l10n_din5008_template_data = fields.Binary(compute='_compute_l10n_din5008_template_data')
    l10n_din5008_document_title = fields.Char(compute='_compute_l10n_din5008_document_title')

    def _compute_l10n_din5008_template_data(self):
        for record in self:
            record.l10n_din5008_template_data = []

    def _compute_l10n_din5008_document_title(self):
        for record in self:
            record.l10n_din5008_document_title = ''
