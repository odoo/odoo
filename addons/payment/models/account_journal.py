# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.constrains('type')
    def _check_journal_type_change(self):
        acquirer_incompatible_journals = self.filtered(lambda j: j.type not in ('bank', 'cash'))
        if acquirer_incompatible_journals and self.env['payment.acquirer'].search_count([('journal_id', 'in', acquirer_incompatible_journals.ids)]):
            raise ValidationError(_("An acquirer is using this journal. Only bank and cash types are allowed."))

    def _get_unlink_journals(self):
        journals = super()._get_unlink_journals()
        acquirer_journals = self.env['payment.acquirer'].search([('journal_id', 'in', self.ids)])
        journals |= acquirer_journals.mapped('journal_id')
        return journals
