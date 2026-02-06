# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # -- DIAN Authorized Numbering Range --
    l10n_co_edi_dian_authorization = fields.Char(
        string='DIAN Authorization Number',
        help='Authorization number from DIAN resolution for this numbering range.',
    )
    l10n_co_edi_dian_authorization_date = fields.Date(
        string='Authorization Date',
        help='Date of the DIAN resolution authorizing this numbering range.',
    )
    l10n_co_edi_dian_prefix = fields.Char(
        string='DIAN Prefix',
        help='Invoice prefix authorized by DIAN (e.g., SETP, FV, NC).',
    )
    l10n_co_edi_dian_range_from = fields.Integer(
        string='Range From',
        help='First number in the DIAN-authorized numbering range.',
    )
    l10n_co_edi_dian_range_to = fields.Integer(
        string='Range To',
        help='Last number in the DIAN-authorized numbering range.',
    )
    l10n_co_edi_dian_range_valid_from = fields.Date(
        string='Range Valid From',
        help='Start date of the authorized numbering range validity period.',
    )
    l10n_co_edi_dian_range_valid_to = fields.Date(
        string='Range Valid To',
        help='End date of the authorized numbering range validity period.',
    )
    l10n_co_edi_dian_technical_key = fields.Char(
        string='Technical Key (Clave Tecnica)',
        groups='base.group_system',
        help='Technical key from DIAN authorization. Used in CUFE computation for invoices.',
    )

    # -- Contingency --
    l10n_co_edi_is_contingency = fields.Boolean(
        string='Contingency Journal',
        default=False,
        help='If enabled, this journal is used for contingency invoicing when DIAN is unavailable.',
    )

    # -- Computed alerts --
    l10n_co_edi_range_remaining = fields.Integer(
        string='Numbers Remaining',
        compute='_compute_l10n_co_edi_range_remaining',
        help='Remaining numbers in the authorized range.',
    )

    def _compute_l10n_co_edi_range_remaining(self):
        for journal in self:
            if journal.l10n_co_edi_dian_range_to and journal.l10n_co_edi_dian_range_from:
                # Get the highest sequence number used in this journal
                last_move = self.env['account.move'].search([
                    ('journal_id', '=', journal.id),
                    ('state', '=', 'posted'),
                ], order='name desc', limit=1)
                if last_move and journal.l10n_co_edi_dian_prefix:
                    # Extract the numeric part after the prefix
                    name = last_move.name or ''
                    prefix = journal.l10n_co_edi_dian_prefix
                    if name.startswith(prefix):
                        try:
                            current_num = int(name[len(prefix):])
                            journal.l10n_co_edi_range_remaining = journal.l10n_co_edi_dian_range_to - current_num
                            continue
                        except (ValueError, TypeError):
                            pass
                journal.l10n_co_edi_range_remaining = (
                    journal.l10n_co_edi_dian_range_to - journal.l10n_co_edi_dian_range_from + 1
                )
            else:
                journal.l10n_co_edi_range_remaining = 0

    @api.constrains('l10n_co_edi_dian_range_from', 'l10n_co_edi_dian_range_to')
    def _check_dian_range(self):
        for journal in self:
            if journal.l10n_co_edi_dian_range_from and journal.l10n_co_edi_dian_range_to:
                if journal.l10n_co_edi_dian_range_from > journal.l10n_co_edi_dian_range_to:
                    raise UserError(_('DIAN range "From" must be less than or equal to "To".'))
