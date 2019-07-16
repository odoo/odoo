# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_latam_use_documents = fields.Boolean(
        'Use Documents?',
    )
    l10n_latam_company_use_documents = fields.Boolean(
        compute='_compute_l10n_latam_company_use_documents',
    )
    l10n_latam_country_code = fields.Char(
        related='company_id.country_id.code',
        help='Technical field used to hide/show fields regarding the '
        'localization'
    )

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
            if rec.env['account.invoice'].search(
                    [('journal_id', '=', rec.id)]):
                raise ValidationError(_(
                    'You can not modify the field "Use Documents?"'
                    ' if invoices already exist in the journal!'))

    def create_document_type_sequences(self):
        """ Method to be inherited by different localizations.
        """
        return True
