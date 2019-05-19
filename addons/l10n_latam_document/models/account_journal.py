# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_latam_use_documents = fields.Boolean(
        'Use Documents?',
    )
    l10n_latam_country_code = fields.Char(
        related='company_id.country_id.code',
        help='Technical field used to hide/show fields regarding the '
        'localization'
    )

    @api.onchange('company_id', 'type')
    def change_company(self):
        self.l10n_latam_use_documents = self.type in ['sale', 'purchase'] and \
           self.company_id.l10n_latam_use_documents

    @api.constrains('l10n_latam_use_documents')
    def check_use_document(self):
        for rec in self:
            if rec.env['account.invoice'].search(
                    [('journal_id', '=', rec.id)]):
                raise ValidationError(_(
                    'You can not modify the field "Use Documents?"'
                    ' if invoices already exist in the journal!'))

    def get_document_type_sequence(self, invoice):
        """ Method to be inherited by different localizations.
        """
        self.ensure_one()
        return self.env['ir.sequence']

    def create_document_type_sequences(self):
        """ Method to be inherited by different localizations.
        """
        return True
