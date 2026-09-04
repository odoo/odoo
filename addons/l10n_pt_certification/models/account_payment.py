import re

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError

from odoo.addons.l10n_pt_certification.models.l10n_pt_at_series import AT_SERIES_ACCOUNTING_DOCUMENT_TYPES


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_pt_atcud = fields.Char(
        string='Portuguese ATCUD',
        compute='_compute_l10n_pt_atcud', store=True,
        help="Unique document code formed by the AT series validation code and the number of the document.",
    )
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        compute='_compute_l10n_pt_document_number', store=True,
        help="Unique identifier for Portuguese documents, made up of the internal document type code, the series name, "
             "and the number of the document within the series.",
    )
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        compute='_compute_l10n_pt_at_series_id',
        readonly=False, store=True,
    )
    l10n_pt_at_series_line_id = fields.Many2one(
        comodel_name="l10n_pt.at.series.line",
        string="Document-specific AT Series",
        compute='_compute_l10n_pt_at_series_line_id',
    )
    # Document type used in invoice template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Selection(
        selection=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES,
        string="Portuguese Document Type",
        compute='_compute_l10n_pt_document_type',
        store=True,
    )
    l10n_pt_print_version = fields.Selection(
        selection=[
            ('original', 'Original print'),
            ('reprint', 'Reprint'),
        ],
        string="Version of Printed Document",
        copy=False,
    )
    l10n_pt_cancel_reason = fields.Char(
        string="Reason for Cancellation",
        copy=False,
        help="Reason given by the user for cancelling this payment",
        readonly=True,
    )

    def is_pt_inbound(self):
        return self.country_code == 'PT' and self.payment_type == 'inbound'

    ####################################
    # OVERRIDES
    ####################################

    def action_post(self):
        for payment in self.filtered(lambda p: p.is_pt_inbound()).sorted('date'):
            payment._check_l10n_pt_document_number()
            payment._check_l10n_pt_dates()
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

    def update_l10n_pt_print_version(self):
        for payment in self.filtered(lambda p: p.country_code == 'PT'):
            if not payment.l10n_pt_print_version:
                payment.l10n_pt_print_version = 'original'
            else:
                payment.l10n_pt_print_version = 'reprint'

    @api.depends('state', 'date', 'country_code')
    def _compute_l10n_pt_show_future_date_warning(self):
        """
        No other documents may be issued with the current or previous date within the same series as
        a document issued in the future. If user enters an invoice date ahead of current date,
        a warning will be displayed.
        """
        for payment in self:
            payment.l10n_pt_show_future_date_warning = (
                payment.is_pt_inbound()
                and payment.state == 'draft'
                and payment.date
                and payment.date > fields.Date.today()
            )

    def _check_l10n_pt_dates(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        self.ensure_one()
        if self.l10n_pt_at_series_id:
            max_payment_date = self.env['account.payment'].search([
                ('state', 'in', ['in_process', 'paid', 'cancel']),
                ('l10n_pt_at_series_id', '=', self.l10n_pt_at_series_id.id),
                ('payment_type', '=', 'inbound'),
            ], order='date desc', limit=1).date

            if (
                max_payment_date
                and max_payment_date > fields.Date.today()
                and (self.date or fields.Date.context_today(self)) < max_payment_date
            ):
                raise UserError(_("You cannot create a payment with a date earlier than the date of the last "
                                  "payment issued in this AT series."))

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    @api.depends('payment_type', 'company_id', 'date', 'journal_id')
    def _compute_l10n_pt_at_series_id(self):
        payments = self.filtered(
            lambda p: not p.l10n_pt_at_series_id or p.l10n_pt_at_series_id.payment_journal_id != p.journal_id
        )
        # Group payments by company and journal
        for (company, journal), grouped_payments in payments.grouped(lambda p: (p.company_id, p.journal_id)).items():
            last_payment = self.env['account.payment'].search([
                ('company_id', '=', company.id),
                ('payment_type', '=', 'inbound'),
                ('journal_id', '=', journal.id)
            ], order='id desc', limit=1)
            at_series = last_payment.l10n_pt_at_series_id or self.env['l10n_pt.at.series'].search([
                '|',
                '&',
                ('company_id', '=', company.id),
                ('company_exclusive_series', '=', True),
                '&',
                ('company_id', 'in', company.parent_ids.ids),
                ('company_exclusive_series', '=', False),
                ('active', '=', True),
                ('payment_journal_id', '=', journal.id),
            ], limit=1)
            grouped_payments.l10n_pt_at_series_id = at_series

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        for payment in self.filtered(lambda p: p.is_pt_inbound()):
            if not payment.l10n_pt_at_series_id:
                raise UserError(_("Please select a series for this payment."))
            if not payment.l10n_pt_at_series_id.active:
                raise UserError(_("An inactive series cannot be used."))

    @api.depends('l10n_pt_at_series_id')
    def _compute_l10n_pt_at_series_line_id(self):
        for (document_type, series), payments in self.grouped(lambda p: (p.l10n_pt_document_type, p.l10n_pt_at_series_id)).items():
            payments.l10n_pt_at_series_line_id = series._get_line_for_type(document_type) if series else None

    @api.depends('l10n_pt_at_series_line_id', 'payment_type', 'country_code', 'state')
    def _compute_l10n_pt_document_number(self):
        for payment in self:
            if payment.is_pt_inbound() and payment.l10n_pt_at_series_line_id:
                if payment.state in ('in_process', 'paid') and not payment.l10n_pt_document_number:
                    payment.l10n_pt_document_number = payment.l10n_pt_at_series_line_id._l10n_pt_get_document_number_sequence().next_by_id()
            else:
                payment.l10n_pt_document_number = False

    def _check_l10n_pt_document_number(self):
        for payment in self.filtered(lambda p: p.is_pt_inbound() and p.l10n_pt_at_series_id):
            if not payment.l10n_pt_at_series_line_id:
                action_error = {
                    'view_mode': 'form',
                    'name': _('AT Series'),
                    'res_model': 'l10n_pt.at.series',
                    'res_id': payment.l10n_pt_at_series_id.id,
                    'type': 'ir.actions.act_window',
                    'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form']],
                    'target': 'new',
                }
                raise RedirectWarning(
                    _("There is no AT series for payments registered under the series name %(series_name)s. "
                      "Create a new series or view existing series via the Accounting Settings.",
                      series_name=payment.l10n_pt_at_series_id.name),
                    action_error,
                    _("Add an AT Series"),
                )
            if payment.l10n_pt_document_number and not re.match(r'^[^ ]+ [^/^ ]+/[0-9]+$', payment.l10n_pt_document_number):
                raise ValidationError(_(
                    "The document number (%s) is invalid. It must start with the internal "
                    "of the document type, a space, the name of the series followed by a slash and the number of the "
                    "document within the series (e.g. RG 2025A/1). Please check if the series selected fulfill these "
                    "requirements.", payment.l10n_pt_document_number
                ))

    @api.depends('country_code', 'payment_type')
    def _compute_l10n_pt_document_type(self):
        for payment in self:
            if payment.is_pt_inbound():
                payment.l10n_pt_document_type = 'payment_receipt'
            else:
                payment.l10n_pt_document_type = False

    @api.depends('l10n_pt_document_number')
    def _compute_l10n_pt_atcud(self):
        for payment in self:
            if payment.is_pt_inbound() and not payment.l10n_pt_atcud and payment.state in ('in_process', 'paid'):
                current_seq_number = int(payment.l10n_pt_document_number.split('/')[-1])
                payment.l10n_pt_atcud = f"{payment.l10n_pt_at_series_line_id._get_at_code()}-{current_seq_number}"
