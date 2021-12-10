from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_latam_use_checkbooks = fields.Boolean(
        string='Use checkbooks?', compute="_compute_l10n_latam_use_checkbooks", store=True, readonly=False)
    l10n_latam_checkbook_ids = fields.One2many(
        'l10n_latam.checkbook', 'journal_id', 'Checkbooks', context={'active_test': False},)

    def _default_outbound_payment_methods(self):
        if self._context.get('third_checks_journal'):
            return self.env.ref('l10n_latam_check.account_payment_method_out_third_checks')
        return super()._default_outbound_payment_methods()

    def _default_inbound_payment_methods(self):
        if self._context.get('third_checks_journal'):
            return self.env.ref('l10n_latam_check.account_payment_method_new_third_checks') + \
                self.env.ref('l10n_latam_check.account_payment_method_in_third_checks')
        return super()._default_inbound_payment_methods()

    @api.depends('outbound_payment_method_line_ids', 'country_code')
    def _compute_l10n_latam_use_checkbooks(self):
        for rec in self.filtered(
                lambda x: x.country_code == 'AR' and
                'check_printing' in x.outbound_payment_method_line_ids.mapped('code')):
            rec.l10n_latam_use_checkbooks = True
