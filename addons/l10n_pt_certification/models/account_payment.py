from odoo import api, fields, models
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

    def _l10n_pt_country_ok(self):
        # Only a PT inbound payment is a PT document: a receipt (RG).
        self.ensure_one()
        return self.country_code == 'PT' and self.payment_type == 'inbound'

    def _l10n_pt_is_cancelled(self):
        self.ensure_one()
        return self.state == 'canceled'

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
        pt_payments = self.filtered(lambda p: p._l10n_pt_country_ok()).sorted('date')
        # A receipt references the document number of the invoices it pays.
        pt_payments.invoice_ids._l10n_pt_check_issued(self.env._("A receipt"))
        pt_payments._check_l10n_pt_dates()
        # A receipt takes its number now: its series must be valid on its date.
        pt_payments.filtered(lambda p: not p.l10n_pt_document_number)._check_l10n_pt_at_series_id()
        pt_payments._set_l10n_pt_document_number()
        return super().action_post()

    def action_cancel(self):
        res = super().action_cancel()
        self.filtered(lambda p: p.state == 'canceled')._l10n_pt_record_cancellation()
        return res

    def write(self, vals):
        if (
            'l10n_pt_at_series_id' in vals
            and self.filtered(lambda p: p.country_code == 'PT' and p.state in ('in_process', 'paid', 'canceled'))
        ):
            raise UserError(self.env._("The AT Series of a payment being processed, paid or canceled cannot be changed."))
        return super().write(vals)

    def action_open_reprint_wizard(self):
        """ PT requirement: documents being reprinted require a reprint reason """
        if self.filtered(lambda p: p.country_code == 'PT' and p.l10n_pt_print_version):
            return self.env['ir.actions.act_window']._for_xml_id('l10n_pt_certification.action_open_reprint_wizard')
        return self.env.ref('account.action_report_payment_receipt').report_action(self)

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    @api.depends('payment_type', 'company_id', 'date', 'journal_id')
    def _compute_l10n_pt_at_series_id(self):
        today = fields.Date.context_today(self)
        at_series_model = self.env['l10n_pt.at.series']
        unissued = self.filtered(lambda p: not p.l10n_pt_document_number)
        # Only a PT inbound payment is issued, as a receipt (RG), in an AT series.
        unissued.filtered(lambda p: not p._l10n_pt_country_ok()).l10n_pt_at_series_id = False
        # A receipt not issued yet moves on from a series that has ended, so a series can be closed.
        payments = unissued.filtered(lambda p: p._l10n_pt_country_ok() and (
            not p.l10n_pt_at_series_id.active
            or p.l10n_pt_at_series_id.journal_id != p.journal_id
            or not p.l10n_pt_at_series_id._l10n_pt_is_valid_on(p.date or today)
        ))
        for (company, journal, date), grouped_payments in payments.grouped(
            lambda p: (p.company_id, p.journal_id, p.date or today)
        ).items():
            last_payment = self.env['account.payment'].search([
                ('company_id', '=', company.id),
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', journal.id),
                ('l10n_pt_document_type', '=', 'payment_receipt'),
                ('l10n_pt_at_series_id.active', '=', True),
                *at_series_model._l10n_pt_validity_domain(date, prefix='l10n_pt_at_series_id.'),
            ], order='id desc', limit=1)
            at_series = last_payment.l10n_pt_at_series_id or at_series_model.search([
                *at_series_model._l10n_pt_company_domain(company),
                *at_series_model._l10n_pt_validity_domain(date),
                ('document_type', '=', 'payment_receipt'),
                ('active', '=', True),
                ('journal_id', '=', journal.id),
            ], limit=1)
            grouped_payments.l10n_pt_at_series_id = at_series

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        super()._check_l10n_pt_at_series_id()
