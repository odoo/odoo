# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class SDDMandate(models.Model):
    """ A class containing the data of a mandate sent by a customer to give its
    consent to a company to collect the payments associated to his invoices
    using SEPA Direct Debit.
    """
    _name = 'sdd.mandate'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = 'SDD Mandate'
    _check_company_auto = True

    _sql_constraints = [('name_unique', 'unique(name)', "Mandate identifier must be unique! Please choose another one.")]

    state = fields.Selection([('draft', 'Draft'),('active','Active'), ('revoked','Revoked'), ('closed','Closed')],
                            string="State",
                            readonly=True,
                            default='draft',
                            help="The state this mandate is in. \n"
                            "- 'draft' means that this mandate still needs to be confirmed before being usable. \n"
                            "- 'active' means that this mandate can be used to pay invoices. \n"
                            "- 'closed' designates a mandate that has been marked as not to use anymore without invalidating the previous transactions done with it."
                            "- 'revoked' means the mandate has been signaled as fraudulent by the customer. It cannot be used anymore, and should not ever have been. You will probably need to refund the related invoices, if any.\n")

    #one-off mandates are fully supported, but hidden to the user for now. Let's see if they need it.
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
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, help="Company for whose invoices the mandate can be used.")
    partner_bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string='IBAN',
        check_company=True,
        help="Account of the customer to collect payments from.",
    )
    start_date = fields.Date(string="Start Date", required=True, help="Date from which the mandate can be used (inclusive).")
    end_date = fields.Date(string="End Date", help="Date until which the mandate can be used. It will automatically be closed after this date.")
    payment_journal_id = fields.Many2one(
        string='Journal',
        comodel_name='account.journal',
        required=True,
        check_company=True,
        domain="[('id', 'in', suitable_journal_ids)]",
        help='Journal to use to receive SEPA Direct Debit payments from this mandate.',
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
        help="Payments generated thanks to this mandate.")
    payments_to_collect_nber = fields.Integer(string='Direct Debit Payments to Collect',
        compute='_compute_from_moves',
        help="Number of Direct Debit payments to be collected for this mandate, that is, the number of payments that "
             "have been generated and posted thanks to this mandate and still needs their XML file to be generated and "
             "sent to the bank to debit the customer's account.")
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')

    @api.depends('company_id')
    def _compute_suitable_journal_ids(self):
        for m in self:
            company_id = m.company_id.id or self.env.company.id
            domain = [
                *self.env['account.journal']._check_company_domain(company_id),
                ('type', '=', 'bank'),
            ]
            payment_method = self.env.ref('account_sepa_direct_debit.payment_method_sdd')

            # Get all journals which have the payment method sdd
            m.suitable_journal_ids = self.env['account.journal'].search(domain).filtered(
                lambda j: payment_method in j.inbound_payment_method_line_ids.mapped('payment_method_id')
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise UserError(_("Only mandates in draft state can be deleted from database when cancelled."))

    @api.model
    def _sdd_get_usable_mandate(self, company_id, partner_id, date):
        """ returns the first mandate found that can be used, accordingly to given parameters
        or none if there is no such mandate.
        """
        self.flush_model(['state', 'start_date', 'end_date', 'company_id', 'partner_id', 'one_off'])

        query_obj = self._where_calc([
            ('state', 'not in', ['draft', 'revoked']),
            ('start_date', '<=', date),
            '|', ('end_date', '>=', date), ('end_date', '=', None),
            ('company_id', '=', company_id),
            ('partner_id', '=', partner_id),
        ])
        tables, where_clause, where_clause_params = query_obj.get_sql()

        self._cr.execute('''
            SELECT sdd_mandate.id
            FROM ''' + tables + '''
            WHERE ''' + where_clause + '''
            AND
            (
                (
                    SELECT COUNT(payment.id)
                    FROM account_payment payment
                    JOIN account_move move ON move.id = payment.move_id
                    WHERE move.sdd_mandate_id = sdd_mandate.id
                )  = 0
                OR
                sdd_mandate.one_off IS FALSE
            )
            LIMIT 1
        ''', where_clause_params)
        res = self._cr.fetchone()
        return res and self.browse(res[0]) or self.env['sdd.mandate']

    @api.depends()
    def _compute_from_moves(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_mandates = self.filtered('id')
        if not stored_mandates:
            self.paid_invoices_nber = 0
            self.payments_to_collect_nber = 0
            self.paid_invoice_ids = False
            self.payment_ids = False
            return
        self.env['account.move'].flush_model(['sdd_mandate_id', 'move_type'])

        self._cr.execute('''
            SELECT
                move.sdd_mandate_id,
                ARRAY_AGG(move.id) AS invoice_ids
            FROM account_move move
            WHERE move.sdd_mandate_id IS NOT NULL
            AND move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
            GROUP BY move.sdd_mandate_id
        ''')
        query_res = dict((mandate_id, invoice_ids) for mandate_id, invoice_ids in self._cr.fetchall())

        for mandate in self:
            invoice_ids = query_res.get(mandate.id, [])
            mandate.paid_invoice_ids = [(6, 0, invoice_ids)]
            mandate.paid_invoices_nber = len(invoice_ids)

        self._cr.execute('''
            SELECT
                move.sdd_mandate_id,
                ARRAY_AGG(payment.id) AS payment_ids
            FROM account_payment payment
            JOIN account_payment_method method ON method.id = payment.payment_method_id
            JOIN account_move move ON move.id = payment.move_id
            WHERE move.sdd_mandate_id IS NOT NULL
            AND move.state = 'posted'
            AND method.code IN %s
            GROUP BY move.sdd_mandate_id
        ''', [tuple(self.payment_ids.payment_method_id._get_sdd_payment_method_code())])
        query_res = dict((mandate_id, payment_ids) for mandate_id, payment_ids in self._cr.fetchall())

        for mandate in self:
            payment_ids = query_res.get(mandate.id, [])
            mandate.payment_ids = [(6, 0, payment_ids)]
            mandate.payments_to_collect_nber = len(payment_ids)

    def action_validate_mandate(self):
        """ Called by the 'validate' button of the form view.
        """
        for record in self:
            if record.state == 'draft':
                if not record.partner_bank_id:
                    raise UserError(_("A debtor account is required to validate a SEPA Direct Debit mandate."))
                if record.partner_bank_id.acc_type != 'iban':
                    raise UserError(_("SEPA Direct Debit scheme only accepts IBAN account numbers. Please select an IBAN-compliant debtor account for this mandate."))

                record.state = 'active'

    def action_cancel_draft_mandate(self):
        """ Cancels (i.e. deletes) a mandate in draft state.
        """
        self.unlink()

    def action_revoke_mandate(self):
        """ Called by the 'revoke' button of the form view.
        """
        for record in self:
            record.state = 'revoked'

    def action_close_mandate(self):
        """ Called by the 'close' button of the form view.
        Also automatically triggered by one-off mandate when they are used.
        """
        for record in self:
            if record.state != 'revoked':
                record.end_date = fields.Date.today()
                record.state = 'closed'

    def action_view_paid_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paid Invoices'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.mapped('paid_invoice_ids').ids)],
        }

    def action_view_payments_to_collect(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments to Collect'),
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.mapped('payment_ids').ids), ('state', '=', 'posted')],
        }

    @api.constrains('end_date', 'start_date')
    def validate_end_date(self):
        for record in self:
            if record.end_date and record.start_date and record.end_date < record.start_date:
                raise UserError(_("The end date of the mandate must be posterior or equal to its start date."))

    @api.constrains('payment_journal_id')
    def _validate_account_journal_id(self):
        for record in self:
            if record.payment_journal_id.bank_account_id.acc_type != 'iban':
                raise UserError(_("Only IBAN account numbers can receive SEPA Direct Debit payments. Please select a journal associated to one."))

    @api.constrains('debtor_id_code')
    def _validate_debtor_id_code(self):
        for record in self:
            if record.debtor_id_code and len(record.debtor_id_code) > 35:  # Arbitrary limitation given by SEPA regulation for the <id> element used for this field when generating the XML
                raise UserError(_("The debtor identifier you specified exceeds the limitation of 35 characters imposed by SEPA regulation"))

    @api.constrains('partner_id')
    def _validate_partner_id(self):
        for mandate in self:
            for pay in mandate.payment_ids:
                if mandate.partner_id != pay.partner_id.commercial_partner_id:
                    raise UserError(_("Trying to register a payment on a mandate belonging to a different partner."))

    @api.model
    def cron_update_mandates_states(self):
        current_company = self.env.company
        today = fields.Date.today()
        for mandate in self.search([('company_id', '=', current_company.id), ('state', '=', 'active'), ('end_date', '!=', False)]):
            if mandate.end_date < today:
                mandate.state = 'closed'
