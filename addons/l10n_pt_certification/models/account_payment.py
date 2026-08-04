from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pt_certification.models.l10n_pt_at_series import AT_SERIES_ACCOUNTING_DOCUMENT_TYPES


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'l10n.pt.document.mixin']

    _l10n_pt_document_type_depends = ('country_code', 'payment_type')

    l10n_pt_at_series_id = fields.Many2one(
        compute='_compute_l10n_pt_at_series_id',
        readonly=False, store=True,
        domain="[('journal_id', '=', journal_id)]",
    )
    l10n_pt_document_type = fields.Selection(selection_add=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES)

    def is_pt_inbound(self):
        return self.country_code == 'PT' and self.payment_type == 'inbound'

    def _l10n_pt_country_ok(self):
        self.ensure_one()
        return self.is_pt_inbound()

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.date

    def _l10n_pt_get_document_type(self):
        self.ensure_one()
        return 'payment_receipt'

    ####################################
    # OVERRIDES
    ####################################

    def action_post(self):
        pt_payments = self.filtered(lambda p: p.is_pt_inbound()).sorted('date')
        pt_payments._check_l10n_pt_dates()
        pt_payments._set_l10n_pt_document_number()
        return super().action_post()

    def write(self, vals):
        if (
            'l10n_pt_at_series_id' in vals
            and self.filtered(lambda p: p.country_code == 'PT' and p.state in ('in_process', 'paid', 'canceled'))
        ):
            raise UserError(_("The AT Series of a payment being processed, paid or canceled cannot be changed."))
        return super().write(vals)

    def action_open_reprint_wizard(self):
        """ PT requirement: documents being reprinted require a reprint reason """
        if self.filtered(lambda p: p.country_code == 'PT' and p.l10n_pt_print_version):
            return self.env.ref('l10n_pt_certification.action_open_reprint_wizard').read()[0]
        return self.env.ref('account.action_report_payment_receipt').report_action(self)

    ####################################
    # MISC REQUIREMENTS
    ####################################

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    @api.depends('payment_type', 'company_id', 'date', 'journal_id')
    def _compute_l10n_pt_at_series_id(self):
        payments = self.filtered(
            lambda p: not p.l10n_pt_at_series_id or p.l10n_pt_at_series_id.journal_id != p.journal_id
        )
        # Group payments by company and journal
        for (company, journal), grouped_payments in payments.grouped(lambda p: (p.company_id, p.journal_id)).items():
            last_payment = self.env['account.payment'].search([
                ('company_id', '=', company.id),
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', journal.id),
                ('l10n_pt_document_type', '=', 'payment_receipt')
            ], order='id desc', limit=1)
            at_series = last_payment.l10n_pt_at_series_id or self.env['l10n_pt.at.series'].search([
                *self.env['l10n_pt.at.series']._l10n_pt_company_domain(company),
                ('document_type', '=', 'payment_receipt'),
                ('active', '=', True),
                ('journal_id', '=', journal.id),
            ], limit=1)
            grouped_payments.l10n_pt_at_series_id = at_series

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        super()._check_l10n_pt_at_series_id()
