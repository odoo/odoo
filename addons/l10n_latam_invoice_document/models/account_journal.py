# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_latam_use_documents = fields.Boolean(
        'Use Documents?', help="If active: will be using for legal invoicing (invoices, debit/credit notes)."
        " If not set means that will be used to register accounting entries not related to invoicing legal documents."
        " For Example: Receipts, Tax Payments, Register journal entries")
    l10n_latam_company_use_documents = fields.Boolean(compute='_compute_l10n_latam_company_use_documents')

    @api.depends('company_id')
    def _compute_l10n_latam_company_use_documents(self):
        for rec in self:
            rec.l10n_latam_company_use_documents = rec.company_id._localization_use_documents()

    @api.onchange('company_id', 'type')
    def _onchange_company(self):
        self.l10n_latam_use_documents = self.type in ['sale', 'purchase'] and \
            self.l10n_latam_company_use_documents

    @api.constrains('l10n_latam_use_documents')
    def check_use_document(self):
        for rec in self:
            if rec.env['account.move'].search([('journal_id', '=', rec.id), ('posted_before', '=', True)], limit=1):
                raise ValidationError(_(
                    'You can not modify the field "Use Documents?" if there are validated invoices in this journal!'))

    @api.onchange('type', 'l10n_latam_use_documents')
    def _onchange_type(self):
        res = super()._onchange_type()
        if self.l10n_latam_use_documents:
            self.refund_sequence = False
        return res
