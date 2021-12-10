from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_latam_use_checkbooks = fields.Boolean(
        string='Use checkbooks?',
        compute="_compute_l10n_latam_use_checkbooks", inverse='_inverse_l10n_latam_use_checkbooks', store=True,
        readonly=False,
        copy=False,
    )
    l10n_latam_checkbook_ids = fields.One2many(
        comodel_name='l10n_latam.checkbook',
        inverse_name='journal_id',
        string='Checkbooks',
    )

    @api.depends('outbound_payment_method_line_ids', 'check_manual_sequencing')
    def _compute_l10n_latam_use_checkbooks(self):
        """ If check_manual_sequencing is selected or no check_printing payment method, disable use checkbooks"""
        self.filtered(
            lambda x: x.check_manual_sequencing or
            'check_printing' not in x.outbound_payment_method_line_ids.mapped('code')).l10n_latam_use_checkbooks = False

    @api.onchange('l10n_latam_use_checkbooks')
    def _inverse_l10n_latam_use_checkbooks(self):
        self.filtered('l10n_latam_use_checkbooks').check_manual_sequencing = False
