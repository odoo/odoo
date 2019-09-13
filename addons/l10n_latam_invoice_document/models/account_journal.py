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
    l10n_latam_country_code = fields.Char(
        related='company_id.country_id.code', help='Technical field used to hide/show fields regarding the localization')

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
            if rec.env['account.move'].search([('journal_id', '=', rec.id), ('state', '!=', 'draft')]):
                raise ValidationError(_(
                    'You can not modify the field "Use Documents?" if there are validated invoices in this journal!'))

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('default_type') in ('out_receipt', 'in_receipt'):
            args += [('l10n_latam_use_documents', '=', False)]
        return super()._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)
