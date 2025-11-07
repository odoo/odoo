from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        compute='_compute_l10n_pt_at_series_id',
        domain="[('payment_journal_id', '=', available_l10n_pt_at_series_ids)]",
        readonly=False, store=True,
    )
    available_l10n_pt_at_series_ids = fields.Many2many('l10n_pt.at.series', compute="_compute_available_l10n_pt_at_series_ids")

    @api.depends('payment_type', 'journal_id')
    def _compute_available_l10n_pt_at_series_ids(self):
        inbound_wizards = self.filtered(lambda w: w.journal_id and w.payment_type == 'inbound' and w.country_code == 'PT')
        for journal, wizards in inbound_wizards.grouped('journal_id').items():
            wizards.available_l10n_pt_at_series_ids = self.env['l10n_pt.at.series'].search([
                '|',
                '&',
                ('company_id', '=', wizards.company_id.id),
                ('company_exclusive_series', '=', True),
                '&',
                ('company_id', 'in', wizards.company_id.parent_ids.ids),
                ('company_exclusive_series', '=', False),
                ('active', '=', True),
                ('payment_journal_id', '=', journal.id),
            ]).ids

    @api.depends('payment_type', 'company_id', 'journal_id')
    def _compute_l10n_pt_at_series_id(self):
        for wizard in self.filtered(lambda w: w.country_code == 'PT'):
            available_series = wizard.available_l10n_pt_at_series_ids
            if not available_series:
                wizard.l10n_pt_at_series_id = None
                continue

            # Get the last payment with an AT series
            last_payment = self.env['account.payment'].search([
                ('company_id', '=', wizard.company_id.id),
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', wizard.journal_id.id),
                ('l10n_pt_at_series_id', 'in', available_series.ids),
            ], order='id desc', limit=1)

            # If no AT series used in a payment in this journal, fallback to an active series for this journal
            wizard.l10n_pt_at_series_id = last_payment.l10n_pt_at_series_id or available_series[0]._origin

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['l10n_pt_at_series_id'] = self.l10n_pt_at_series_id.id
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals['l10n_pt_at_series_id'] = self.l10n_pt_at_series_id.id
        return payment_vals
