# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command, api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import SQL

SDD_MIN_PRENOT_PERIOD = 2
SDD_FIRST_MIN_PRENOT_PERIOD = 5


class SDDMandate(models.Model):
    """ A class containing the data of a mandate sent by a customer to give its
    consent to a company to collect the payments associated to his invoices
    using SEPA Direct Debit.
    """
    _name = 'sdd.mandate'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = 'SDD Mandate'
    _check_company_auto = True
    _order = 'start_date, id'

    _sql_constraints = [('name_unique', 'unique(name)', "Mandate identifier must be unique! Please choose another one.")]

    def _get_default_start_date(self):
        return fields.Date.context_today(self)

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('cancelled', 'Cancelled'),
            ('revoked', 'Revoked'),
            ('closed', 'Closed'),
        ],
        readonly=True,
        default='draft',
        tracking=True,
        help="Draft: Validate before use.\n"
            "Active: Valid mandates to collect payments.\n"
            "Cancelled: Mandates never validated.\n"
            "Closed: Expired or manually closed mandates. Previous transactions remain valid.\n"
            "Revoked: Fraudulent mandates. Previous invoices might need reimbursement.\n"
    )
    is_sent = fields.Boolean(string="Sent to the customer", default=False)

    # one-off mandates are fully supported, but hidden to the user for now. Let's see if they need it.
    one_off = fields.Boolean(string='One-off Mandate',
                                    default=False,
                                    help="True if and only if this mandate can be used for only one transaction. It will automatically go from 'active' to 'closed' after its first use in payment if this option is set.\n")

    name = fields.Char(string='Identifier', required=True, help="The unique identifier of this mandate.", default=lambda self: datetime.now().strftime('%f%S%M%H%d%m%Y'), copy=False)
    debtor_id_code = fields.Char(string='Debtor Identifier', help="Free reference identifying the debtor in your company.")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required=True,
        check_company=True,
        help="Customer whose payments are to be managed by this mandate.",
    )
    partner_parent_id = fields.Many2one(
        related='partner_id.parent_id',
        comodel_name='res.partner',
        string="Parent Partner",
        readonly=True,
    )
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, help="Company for whose invoices the mandate can be used.")
    partner_bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string='IBAN',
        check_company=True,
        help="Account of the customer to collect payments from.",
    )
    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=_get_default_start_date,
        help="Date from which the mandate can be used (inclusive).",
    )
    end_date = fields.Date(string="End Date", help="Date until which the mandate can be used. It will automatically be closed after this date.")
    expiration_warning_already_sent = fields.Boolean(
        string="Expiration warning sent",
        default=False,
        readonly=True,
        required=True,
        copy=False,
    )
    pre_notification_period = fields.Integer(
        string="Pre-notification",
        default=SDD_MIN_PRENOT_PERIOD, required=True,
        help="The minimum notice period in days, used to inform the customer prior to collection.",
    )
    sdd_scheme = fields.Selection(string="SDD Scheme", selection=[('CORE', 'CORE'), ('B2B', 'B2B')],
        required=True, default='CORE', help='The B2B scheme is an optional scheme,\noffered exclusively to business payers.\n'
        'Some banks/businesses might not accept B2B SDD.',)

    paid_invoice_ids = fields.One2many(string='Invoices Paid', comodel_name='account.move',
        compute='_compute_from_moves',
        help="Invoices paid using this mandate.")
    paid_invoices_nber = fields.Integer(string='Paid Invoices Number',
        compute='_compute_from_moves',
        help="Number of invoices paid with this mandate.")
    payment_ids = fields.One2many(string='Payments', comodel_name='account.payment',
        compute='_compute_from_moves',
        help="In-process and completed payments generated under this mandate.")
    payments_to_collect_nber = fields.Integer(string='Direct Debit Payments to Collect',
        compute='_compute_from_moves',
        help="Number of in-process and completed payments generated under this mandate.")
    mandate_pdf_file = fields.Binary(
        string="Mandate Form PDF",
        attachment=True,
        copy=False,
        readonly=True,
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise UserError(_("Only mandates in draft state can be deleted."))

    @api.model
    def _sdd_get_usable_mandate(self, company_id, partner_id, date):
        """ returns the first mandate found that can be used, accordingly to given parameters
        or none if there is no such mandate.
        """
        mandates = self.env['sdd.mandate'].search([
                ('state', '=', 'active'),
                ('start_date', '<=', date),
                '|', ('end_date', '=', False), ('end_date', '>=', date),
                ('company_id', '=', company_id),
                ('partner_id', '=', partner_id),
            ],
            limit=1,
            order='start_date,id',
        )
        return mandates

    def _compute_from_moves(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_mandates = self.filtered('id')
        if not stored_mandates:
            self.paid_invoices_nber = 0
            self.payments_to_collect_nber = 0
            self.paid_invoice_ids = False
            self.payment_ids = False
            return

        results = dict(
            self.env['account.payment']._read_group([
                ('sdd_mandate_id', 'in', self.ids),
                ('payment_method_code', 'in', self.env['account.payment.method']._get_sdd_payment_method_code()),
                ('state', 'in', ('in_process', 'paid')),
            ], groupby=['sdd_mandate_id'], aggregates=['id:recordset'])
        )

        for mandate in self:
            payments = results.get(mandate, self.env['account.payment'])
            mandate.payment_ids = [Command.set(payments.ids)]
            mandate.payments_to_collect_nber = len(payments)
            invoices = payments.reconciled_invoice_ids.filtered(lambda move: move.payment_state == 'paid')
            mandate.paid_invoice_ids = [Command.set(invoices.ids)]
            mandate.paid_invoices_nber = len(invoices)

    def _update_and_partition_state_by_validity(self):
        """
            Helper method to check whether a mandate can still be used or not (and if we're nearing its expiration date, to warn users)
            This also close mandates that are past their validity date
            :return: tuple containing the mandates recordsets split by their validity (valid, valid but expiring soon, invalid)
            :rtype: dict
        """
        today = fields.Date.context_today(self)
        expiry_date_per_mandate = self._get_expiry_date_per_mandate()
        active_mandates = self.filtered(lambda mandate: mandate.state == 'active')

        valid_mandates = self.env['sdd.mandate']
        expiring_mandates = self.env['sdd.mandate']
        invalid_mandates = self - active_mandates

        to_close = self.env['sdd.mandate']
        for mandate in active_mandates:
            expiry_date = expiry_date_per_mandate[mandate]
            if mandate.start_date <= today <= expiry_date:
                if today + fields.date_utils.relativedelta(days=30) >= expiry_date:
                    expiring_mandates += mandate  # Used to send warnings
                else:
                    valid_mandates += mandate
            elif today < mandate.start_date:
                invalid_mandates += mandate
            else:
                to_close += mandate
                invalid_mandates += mandate

        # Closing invalid mandates that haven't been closed yet
        to_close.state = 'closed'
        return {
            'valid': valid_mandates.with_prefetch(),
            'expiring': expiring_mandates.with_prefetch(),
            'invalid': invalid_mandates.with_prefetch(),
        }

    def _get_expiry_date_per_mandate(self):
        """
        "The mandate expires 36 months after the last initiated collection."
        - SEPA regulation
        """
        expiry_date_per_mandate = {}
        delay_36_months = fields.date_utils.relativedelta(months=36)
        payments_collected_per_mandate = dict(self.env['account.payment']._read_group([
                ('sdd_mandate_id', 'in', self.ids),
                ('payment_method_code', 'in', self.env['account.payment.method']._get_sdd_payment_method_code()),
                ('state', '=', 'paid'),
            ],
            groupby=['sdd_mandate_id'],
            aggregates=['id:recordset'],
        ))
        for mandate in self:
            payments_collected = payments_collected_per_mandate.get(mandate, self.env['account.payment'])

            dates = [mandate.end_date] if mandate.end_date else []
            dates.append(max(payments_collected.mapped('date'), default=mandate.start_date) + delay_36_months)
            expiry_date_per_mandate[mandate] = min(dates)  # Todo use records

        return expiry_date_per_mandate

    def _send_expiry_reminder(self):
        self.ensure_one()
        template = self.env.ref('account_sepa_direct_debit.email_template_sdd_mandate_expiring')
        self.message_post_with_source(
            source_ref=template,
            subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
        )
        self.expiration_warning_already_sent = True

    def action_send_and_print(self):
        self.ensure_one()
        self._ensure_required_data()
        template = self.env.ref('account_sepa_direct_debit.email_template_sdd_new_mandate', raise_if_not_found=False)

        return {
            'name': _("Send"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sdd.mandate.send',
            'target': 'new',
            'context': {
                'default_mandate_id': self.id,
                'default_template_id': template and template.id or False,
            },
        }

    def action_validate_mandate(self):
        """ Called by the 'validate' button of the form view.
        """
        self._ensure_required_data()

        for mandate in self:
            if not mandate.partner_bank_id:
                raise UserError(_("A customer account is required to validate a SEPA Direct Debit mandate."))
            if mandate.partner_bank_id.acc_type != 'iban':
                raise UserError(_(
                    "SEPA Direct Debit scheme only accepts IBAN account numbers. "
                    "Please select an IBAN-compliant debtor account for this mandate."
                ))
            if mandate.state == 'draft':
                mandate.state = 'active'

    def action_revoke_mandate(self):
        """ Called by the 'revoke' button of the form view.
        """
        self.state = 'revoked'

    def action_cancel_mandate(self):
        self.state = 'cancelled'

    def action_close_mandate(self):
        """ Called by the 'close' button of the form view.
        Also automatically triggered by one-off mandate when they are used.
        """
        for record in self:
            if record.state != 'revoked':
                record.end_date = fields.Date.today()
                record.state = 'closed'

    def action_view_paid_invoices(self):
        return self.paid_invoice_ids._get_records_action(name=_('Paid Invoices'))

    def action_view_payments_to_collect(self):
        return self.payment_ids._get_records_action(name=_('Payments to Collect'))

    def action_parent_id_from_sdd_mandate(self):
        parent = self.partner_id.parent_id
        return parent._get_records_action(name=_("Partner's Parent"))

    @api.constrains('end_date', 'start_date')
    def _validate_end_date(self):
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise UserError(_("The end date of the mandate must be posterior or equal to its start date."))

    @api.constrains('debtor_id_code')
    def _validate_debtor_id_code(self):
        for record in self:
            if record.debtor_id_code and len(record.debtor_id_code) > 35:  # Arbitrary limitation given by SEPA regulation for the <id> element used for this field when generating the XML
                raise UserError(_("The debtor identifier you specified exceeds the limitation of 35 characters imposed by SEPA regulation"))

    @api.constrains('pre_notification_period')
    def _validate_pre_notification_period(self):
        for mandate in self:
            if mandate.pre_notification_period < SDD_MIN_PRENOT_PERIOD:  # Minimum required for collection
                raise UserError(_(
                    "SEPA regulations set the minimum pre-notification period to a minimum of %s days "
                    "to allow enough time for the customer to check that their account is adequately funded.",
                    SDD_MIN_PRENOT_PERIOD
                ))

    def _ensure_required_data(self):
        """ Helper to make sure we don't send/validate a mandate missing the required data """
        for mandate in self:
            if mandate.sdd_scheme == 'B2B' and not mandate.partner_id.is_company:
                raise UserError(_("Under B2B SDD Scheme, the customer must be a company."))
            stateless_partners = self.partner_id.filtered(lambda partner: not partner.country_id)
            if stateless_partners:
                msg = _("The customer must have a country")
                if len(stateless_partners) == 1:
                    raise RedirectWarning(
                        msg,
                        action={
                            'name': _("SEPA direct debit stateless customer"),
                            'type': 'ir.actions.act_window',
                            'res_model': 'res.partner',
                            'views': [(False, 'form'), (False, 'list')],
                            'res_id': self.partner_id.id
                        },
                        button_text=_("Open customer"),
                    )
                else:
                    raise RedirectWarning(
                        msg,
                        action={
                            'name': _("SEPA direct debit stateless customer"),
                            'type': 'ir.actions.act_window',
                            'res_model': 'res.partner',
                            'views': [(False, 'list'), (False, 'form')],
                            'domain': [('id', 'in', self.partner_id.ids)],
                        },
                        button_text=_("Open customers"),
                    )

    @api.model
    def cron_update_mandates_states(self):
        mandates = self.search([('state', '=', 'active')])
        mandates_per_validity = mandates._update_and_partition_state_by_validity()
        mandates_per_validity['valid'].expiration_warning_already_sent = False  # Reset the field if a new payment came, resetting the period
        for mandate in mandates_per_validity['expiring'].filtered(lambda sddm: not sddm.expiration_warning_already_sent):
            # Warning 30 days before expiration
            mandate._send_expiry_reminder()
