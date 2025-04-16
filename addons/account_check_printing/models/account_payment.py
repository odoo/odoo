# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.misc import formatLang, format_date
from odoo.tools.sql import column_exists, create_column

INV_LINES_PER_STUB = 9


class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_amount_in_words = fields.Char(
        string="Amount in Words",
        store=True,
        compute='_compute_check_amount_in_words',
    )
    check_manual_sequencing = fields.Boolean(related='journal_id.check_manual_sequencing')
    check_number = fields.Char(
        string="Check Number",
        store=True,
        copy=False,
        compute='_compute_check_number',
        inverse='_inverse_check_number',
        help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
             "or if the current numbering is wrong, you can change it in the journal configuration page.",
    )
    payment_method_line_id = fields.Many2one(index=True)
    show_check_number = fields.Boolean(compute='_compute_show_check_number')

    @api.depends('payment_method_line_id.code', 'check_number')
    def _compute_show_check_number(self):
        for payment in self:
            payment.show_check_number = (
                payment.payment_method_line_id.code == 'check_printing'
                and payment.check_number
            )

    @api.constrains('check_number')
    def _constrains_check_number(self):
        for payment_check in self.filtered('check_number'):
            if not payment_check.check_number.isdecimal():
                raise ValidationError(_('Check numbers can only consist of digits'))

    def _auto_init(self):
        """
        Create compute stored field check_number
        here to avoid MemoryError on large databases.
        """
        if not column_exists(self.env.cr, 'account_payment', 'check_number'):
            create_column(self.env.cr, 'account_payment', 'check_number', 'varchar')

        return super()._auto_init()

    @api.constrains('check_number', 'journal_id')
    def _constrains_check_number_unique(self):
        payment_checks = self.filtered('check_number')
        if not payment_checks:
            return
        self.env.flush_all()
        self.env.cr.execute("""
            SELECT payment.check_number, move.journal_id
              FROM account_payment payment
              JOIN account_move move ON move.id = payment.move_id
              JOIN account_journal journal ON journal.id = move.journal_id,
                   account_payment other_payment
              JOIN account_move other_move ON other_move.id = other_payment.move_id
             WHERE payment.check_number::BIGINT = other_payment.check_number::BIGINT
               AND move.journal_id = other_move.journal_id
               AND payment.id != other_payment.id
               AND payment.id IN %(ids)s
               AND move.state = 'posted'
               AND other_move.state = 'posted'
               AND payment.check_number IS NOT NULL
               AND other_payment.check_number IS NOT NULL
        """, {
            'ids': tuple(payment_checks.ids),
        })
        res = self.env.cr.dictfetchall()
        if res:
            raise ValidationError(_(
                'The following numbers are already used:\n%s',
                '\n'.join(_(
                    '%(number)s in journal %(journal)s',
                    number=r['check_number'],
                    journal=self.env['account.journal'].browse(r['journal_id']).display_name,
                ) for r in res)
            ))

    @api.depends('payment_method_line_id', 'currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        for pay in self:
            if pay.currency_id:
                pay.check_amount_in_words = pay.currency_id.amount_to_text(pay.amount)
            else:
                pay.check_amount_in_words = False

    @api.depends('journal_id', 'payment_method_code')
    def _compute_check_number(self):
        for pay in self:
            if pay.journal_id.check_manual_sequencing and pay.payment_method_code == 'check_printing':
                sequence = pay.journal_id.check_sequence_id
                pay.check_number = sequence.get_next_char(sequence.number_next_actual)
            else:
                pay.check_number = False

    def _inverse_check_number(self):
        for payment in self:
            if payment.check_number:
                sequence = payment.journal_id.check_sequence_id.sudo()
                sequence.padding = len(payment.check_number)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields, attributes)
        # pretend the field 'check_number' to be readonly
        field_desc = result.get('check_number') or {}
        if 'readonly' in field_desc:
            field_desc['readonly'] = True
        return result

    def _get_aml_default_display_name_list(self):
        # Extends 'account'
        self.ensure_one()

        if not self.check_number:
            return super()._get_aml_default_display_name_list()

        result = [
            ('label', _("Checks")),
            ('sep', ' - '),
            ('check_number', self.check_number),
        ]

        if self.memo:
            result += [
                ('sep', ': '),
                ('memo', self.memo),
            ]

        return result

    def action_post(self):
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        for payment in self.filtered(lambda p: p.payment_method_id == payment_method_check and p.check_manual_sequencing):
            sequence = payment.journal_id.check_sequence_id
            payment.check_number = sequence.next_by_id()
        return super(AccountPayment, self).action_post()

    def print_checks(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        valid_payments = self.filtered(lambda r: r.payment_method_line_id.code == 'check_printing' and not r.is_sent)

        if len(valid_payments) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
                              "not have already been reconciled"))
        if any(payment.journal_id != valid_payments[0].journal_id for payment in valid_payments):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))

        if not valid_payments[0].journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            self.env.cr.execute("""
                  SELECT payment.check_number
                    FROM account_payment payment
                   WHERE payment.journal_id = %(journal_id)s
                     AND payment.check_number IS NOT NULL
                ORDER BY payment.check_number::BIGINT DESC
                   LIMIT 1
            """, {
                'journal_id': self.journal_id.id,
            })
            last_check_number = (self.env.cr.fetchone() or (False,))[0]
            number_len = len(last_check_number or "")
            next_check_number = f'{int(last_check_number) + 1:0{number_len}}'

            return {
                'name': _('Print Pre-numbered Checks'),
                'type': 'ir.actions.act_window',
                'res_model': 'print.prenumbered.checks',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'payment_ids': valid_payments.ids,
                    'default_next_check_number': next_check_number,
                }
            }
        else:
            valid_payments.filtered(lambda r: r.state == 'draft').action_post()
            return valid_payments.do_print_checks()

    def action_void_check(self):
        self.action_draft()
        self.action_cancel()

    def do_print_checks(self):
        check_layout = self.journal_id.bank_check_printing_layout or self.company_id.account_check_printing_layout
        redirect_action = self.env.ref('account.action_account_config')
        if not check_layout or check_layout == 'disabled':
            msg = _("You have to choose a check layout. For this, go in Invoicing/Accounting Settings, search for 'Checks layout' and set one.")
            raise RedirectWarning(msg, redirect_action.id, _('Go to the configuration panel'))
        report_action = self.env.ref(check_layout, False)
        if not report_action:
            msg = _("Something went wrong with Check Layout, please select another layout in Invoicing/Accounting Settings and try again.")
            raise RedirectWarning(msg, redirect_action.id, _('Go to the configuration panel'))
        self.write({'is_sent': 'True'})
        return report_action.report_action(self)

    #######################
    #CHECK PRINTING METHODS
    #######################
    def _check_fill_line(self, amount_str):
        return amount_str and (amount_str + ' ').ljust(200, '*') or ''

    def _check_build_page_info(self, i, p):
        multi_stub = self.company_id.account_check_printing_multi_stub
        return {
            'sequence_number': self.check_number,
            'manual_sequencing': self.journal_id.check_manual_sequencing,
            'date': format_date(self.env, self.date),
            'partner_id': self.partner_id,
            'partner_name': self.partner_id.name,
            'currency': self.currency_id,
            'state': self.state,
            'amount': formatLang(self.env, self.amount, currency_obj=self.currency_id) if i == 0 else 'VOID',
            'amount_in_word': self._check_fill_line(self.check_amount_in_words) if i == 0 else 'VOID',
            'memo': self.memo,
            'stub_cropped': not multi_stub and len(self.move_id._get_reconciled_invoices()) > INV_LINES_PER_STUB,
            # If the payment does not reference an invoice, there is no stub line to display
            'stub_lines': p,
        }

    def _check_get_pages(self):
        """ Returns the data structure used by the template: a list of dicts containing what to print on pages.
        """
        stub_pages = self._check_make_stub_pages() or [False]
        pages = []
        for i, p in enumerate(stub_pages):
            pages.append(self._check_build_page_info(i, p))
        return pages

    def _check_make_stub_pages(self):
        """ The stub is the summary of paid invoices. It may spill on several pages, in which case only the check on
            first page is valid. This function returns a list of stub lines per page.
        """
        self.ensure_one()

        def prepare_vals(invoice, partials=None, current_amount=0):
            number = ' - '.join([invoice.name, invoice.ref] if invoice.ref else [invoice.name])

            if invoice.is_outbound() or invoice.move_type == 'in_receipt':
                invoice_sign = 1
                partial_field = 'debit_amount_currency'
            else:
                invoice_sign = -1
                partial_field = 'credit_amount_currency'

            amount_residual = invoice.amount_residual - current_amount
            if invoice.currency_id.is_zero(amount_residual):
                amount_residual_str = '-'
            else:
                amount_residual_str = formatLang(self.env, invoice_sign * amount_residual, currency_obj=invoice.currency_id)
            amount_paid = current_amount if current_amount else sum(partials.mapped(partial_field))

            return {
                'due_date': format_date(self.env, invoice.invoice_date_due),
                'number': number,
                'amount_total': formatLang(self.env, invoice_sign * invoice.amount_total, currency_obj=invoice.currency_id),
                'amount_residual': amount_residual_str,
                'amount_paid': formatLang(self.env, invoice_sign * amount_paid, currency_obj=self.currency_id),
                'currency': invoice.currency_id,
            }

        if self.move_id:
            # Decode the reconciliation to keep only invoices.
            term_lines = self.move_id.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
            invoices = (term_lines.matched_debit_ids.debit_move_id.move_id + term_lines.matched_credit_ids.credit_move_id.move_id)\
                .filtered(lambda x: x.is_outbound(include_receipts=True))

            # Group partials by invoices.
            invoice_map = {invoice: self.env['account.partial.reconcile'] for invoice in invoices}
            for partial in term_lines.matched_debit_ids:
                invoice = partial.debit_move_id.move_id
                if invoice in invoice_map:
                    invoice_map[invoice] |= partial
            for partial in term_lines.matched_credit_ids:
                invoice = partial.credit_move_id.move_id
                if invoice in invoice_map:
                    invoice_map[invoice] |= partial
        else:
            invoices = self.invoice_ids.filtered(lambda x: x.is_outbound(include_receipts=True))
            remaining = self.amount

        stub_lines = []
        type_groups = {
            ('in_invoice', 'in_receipt'): _("Bills"),
            ('out_refund',): _("Refunds"),
        }
        invoices_grouped = invoices.grouped(lambda i: next(group for group in type_groups if i.move_type in group))
        for type_group, invoices in invoices_grouped.items():
            invoices = iter(invoices.sorted(lambda x: x.invoice_date_due or x.date))
            if len(invoices_grouped) > 1:
                stub_lines += [{'header': True, 'name': type_groups[type_group]}]
            if self.move_id:
                stub_lines += [
                    prepare_vals(invoice, partials=invoice_map[invoice])
                    for invoice in invoices
                ]
            else:
                while remaining and (invoice := next(invoices, None)):
                    current_amount = min(remaining, invoice.currency_id._convert(
                        from_amount=invoice.amount_residual,
                        to_currency=self.currency_id,
                    ))
                    stub_lines += [prepare_vals(invoice, current_amount=current_amount)]
                    remaining -= current_amount

        # Crop the stub lines or split them on multiple pages
        if not self.company_id.account_check_printing_multi_stub:
            # If we need to crop the stub, leave place for an ellipsis line
            num_stub_lines = len(stub_lines) > INV_LINES_PER_STUB and INV_LINES_PER_STUB - 1 or INV_LINES_PER_STUB
            stub_pages = [stub_lines[:num_stub_lines]]
        else:
            stub_pages = []
            i = 0
            while i < len(stub_lines):
                # Make sure we don't start the credit section at the end of a page
                if len(stub_lines) >= i + INV_LINES_PER_STUB and stub_lines[i + INV_LINES_PER_STUB - 1].get('header'):
                    num_stub_lines = INV_LINES_PER_STUB - 1 or INV_LINES_PER_STUB
                else:
                    num_stub_lines = INV_LINES_PER_STUB
                stub_pages.append(stub_lines[i:i + num_stub_lines])
                i += num_stub_lines

        return stub_pages
