# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models, fields, _

from odoo.exceptions import UserError, ValidationError

class BACSDirectDebitInstruction(models.Model):
    """ A class containing the data of a Direct Debit Instruction (DDI) sent by a customer to
    give their consent to a company to collect the payments associated with their invoices
    using BACS Direct Debit.

    A DDI is an authorization from the customer to the company, allowing the company to take
    payments from the customer's account as per agreed terms. The customer's bank, as well as
    the company, keep a record of the DDI, which can be cancelled or changed by the customer
    at any time, given that sufficient notice is provided to the company and the bank.
    """
    _name = 'bacs.ddi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'BACS Direct Debit Instruction'

    _sql_constraints = [('name_unique', 'unique(name)', "Direct Debit Instruction identifier must be unique! Please choose another one.")]


    name = fields.Char(string='Identifier', required=True, help="The unique identifier of this DDI.", default=lambda self: datetime.now().strftime('%f%S%M%H%d%m%y'), copy=False)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', required=True, check_company=True, help="Customer whose payments are to be managed by this DDI.")
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company, help="Company for whose invoices the DDI can be used.")
    partner_bank_id = fields.Many2one(string='IBAN', comodel_name='res.partner.bank', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Account of the customer to collect payments from.")
    start_date = fields.Date(default=lambda self: fields.Date.today(), string='Date')
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('revoked', 'Revoked'), ('closed', 'Closed')],
                            string="State",
                            readonly=True,
                            default='draft',
                            help="The state this DDI is in. \n"
                            "- 'draft' means that this DDI still needs to be confirmed before being usable. \n"
                            "- 'active' means that this DDI can be used to pay invoices. \n"
                            "- 'closed' designates a DDI that has been marked as not to use anymore without invalidating the previous transactions done with it."
                            "- 'revoked' means the DDI has been signaled as fraudulent by the customer. It cannot be used anymore, and should not ever have been. You will probably need to refund the related invoices, if any.\n")
    payment_journal_id = fields.Many2one(string='Journal', comodel_name='account.journal', required=True, domain="[('id', 'in', suitable_journal_ids)]", help='Journal to use to receive BACS Direct Debit payments from this DDI.')
    payment_ids = fields.One2many(string='Payments', comodel_name='account.payment',
        compute='_compute_from_moves',
        help="Payments generated thanks to this mandate.")
    paid_invoice_ids = fields.One2many(string='Invoices Paid', comodel_name='account.move',
        compute='_compute_from_moves',
        help="Invoices paid using this mandate.")
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')
    paid_invoices_len = fields.Integer(compute='_compute_from_moves')
    payments_len = fields.Integer(compute='_compute_from_moves')

    @api.depends('company_id')
    def _compute_suitable_journal_ids(self):
        for m in self:
            company_id = m.company_id.id or self.env.company.id
            domain = [('company_id', '=', company_id), ('type', '=', 'bank')]
            payment_method = self.env.ref('l10n_uk_bacs.payment_method_bacs_dd')

            # Get all journals which have the payment method bacs direct debit
            m.suitable_journal_ids = self.env['account.journal'].search(domain).filtered(
                lambda j: payment_method in j.inbound_payment_method_line_ids.mapped('payment_method_id')
            )

    @api.model
    def _bacs_get_usable_ddi(self, company_id, partner_id, date):
        """ returns the first mandate found that can be used, accordingly to given parameters
        or none if there is no such mandate.
        """
        ddi = self.search([
            ('state', 'not in', ['draft', 'revoked', 'closed']),
            ('start_date', '<=', date),
            ('company_id', '=', company_id),
            ('partner_id', '=', partner_id),
        ], limit=1)
        return ddi or self.env['bacs.ddi']

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise UserError(_("Only mandates in draft state can be deleted from database when cancelled."))

    def _compute_from_moves(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_ddis = self.mapped('id')
        if not stored_ddis:
            self.paid_invoices_len = 0
            self.payments_len = 0
            self.paid_invoice_ids = False
            self.payment_ids = False
            return
        self.env['account.move'].flush_model(['move_type'])
        self.env['account.payment'].flush_model(['bacs_ddi_id'])

        self._cr.execute('''
            SELECT
                payment.bacs_ddi_id,
                ARRAY_AGG(rel.invoice_id) AS invoice_ids
            FROM account_payment payment
            JOIN account_move__account_payment rel ON rel.payment_id = payment.id
            WHERE payment.bacs_ddi_id IN %s
            GROUP BY payment.bacs_ddi_id
        ''', [tuple(stored_ddis)])
        query_res = dict((mandate_id, invoice_ids) for mandate_id, invoice_ids in self._cr.fetchall())

        for mandate in self:
            invoice_ids = query_res.get(mandate.id, [])
            mandate.paid_invoice_ids = [(6, 0, invoice_ids)]
            mandate.paid_invoices_len = len(invoice_ids)

        self._cr.execute('''
            SELECT
                payment.bacs_ddi_id,
                ARRAY_AGG(payment.id) AS payment_ids
            FROM account_payment payment
            JOIN account_payment_method method ON method.id = payment.payment_method_id
            JOIN account_move__account_payment rel ON rel.payment_id = payment.id
            JOIN account_move move ON move.id = rel.invoice_id
            WHERE payment.bacs_ddi_id IS NOT NULL
            AND move.state = 'posted'
            AND method.code = 'bacs_dd'
            GROUP BY payment.bacs_ddi_id
        ''')
        query_res = dict((mandate_id, payment_ids) for mandate_id, payment_ids in self._cr.fetchall())

        for mandate in self:
            payment_ids = query_res.get(mandate.id, [])
            mandate.payment_ids = [(6, 0, payment_ids)]
            mandate.payments_len = len(payment_ids)

    def action_validate_ddi(self):
        """ Called by the 'validate' button of the form view.
        """
        for record in self:
            if record.state == 'draft':
                if not record.partner_bank_id:
                    raise UserError(_("A debtor account is required to validate a BACS Direct Debit Instruction."))
                if record.partner_bank_id.acc_type != 'iban':
                    raise UserError(_("BACS Direct Debit scheme only accepts IBAN account numbers. Please select an IBAN-compliant debtor account for this BACS Direct Debit Instruction."))
                if self.partner_bank_id.sanitized_acc_number[:2] != 'GB':
                    raise UserError(_("BACS Direct Debit scheme only accepts UK bank accounts. Please select a UK bank account for this BACS Direct Debit Instruction."))

                record.state = 'active'

    def action_cancel_draft_ddi(self):
        """ Cancels (i.e. deletes) a ddi in draft state.
        """
        if self.state != 'draft':
            raise UserError(_("Only mandates in draft state can be cancelled."))
        self.unlink()

    def action_revoke_ddi(self):
        """ Called by the 'revoke' button of the form view.
        """
        for record in self:
            record.state = 'revoked'

    def action_close_ddi(self):
        """ Called by the 'close' button of the form view.
        Also automatically triggered by one-off ddi when they are used.
        """
        for record in self:
            if record.state != 'revoked':
                record.state = 'closed'

    def action_print_ddi(self):
        if not self.company_id.bacs_sun:
            raise UserError(_("BACS Service User Number is not set on the company."))
        if not self.partner_bank_id.acc_type == 'iban':
            raise UserError(_("BACS Direct Debit scheme only accepts IBAN account numbers. Please select an IBAN-compliant debtor account for this BACS Direct Debit Instruction."))
        if self.partner_bank_id.sanitized_acc_number[:2] != 'GB':
            raise UserError(_("BACS Direct Debit scheme only accepts UK bank accounts. Please select a UK bank account for this BACS Direct Debit Instruction."))
        else:
            return self.env.ref('l10n_uk_bacs.ddi_form_report_main').report_action(self)

    @api.constrains('payment_journal_id')
    def _validate_account_journal_id(self):
        for record in self:
            if record.payment_journal_id.bank_account_id.acc_type != 'iban':
                raise ValidationError(_("Only IBAN account numbers can receive BACS Direct Debit payments. Please select a journal associated to one."))
            if record.payment_journal_id.bank_account_id.sanitized_acc_number[:2] != 'GB':
                raise ValidationError(_("BACS Direct Debit scheme only accepts UK bank accounts. Please select a journal associated to one."))

    @api.constrains('partner_id')
    def _validate_partner_id(self):
        for ddi in self:
            for pay in ddi.payment_ids:
                if ddi.partner_id != pay.partner_id.commercial_partner_id:
                    raise UserError(_("Trying to register a payment on a DDI belonging to a different partner."))

    def action_view_payments_to_collect(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payments to Collect'),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.mapped('payment_ids').ids), ('state', '=', 'posted')],
        }

    def action_view_paid_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paid Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.mapped('paid_invoice_ids').ids)],
        }
