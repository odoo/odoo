# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.fields import Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_in_b2c_invoice_number = fields.Char(string='B2C Invoice Number', readonly=True, copy=False, index='btree_not_null')

    _l10n_in_b2c_invoice_number_unique = models.Constraint(
        'UNIQUE(company_id, l10n_in_b2c_invoice_number)',
        'The Indian B2C invoice number must be unique per company.',
    )

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        # B2C orders are invoiced individually under their B2C invoice number.
        if len(self) == 1 and self._is_l10n_in_b2c_order() and self.l10n_in_b2c_invoice_number:
            vals['name'] = self.l10n_in_b2c_invoice_number
        return vals

    def _generate_pos_order_invoice(self):
        if any(order.country_code != 'IN' for order in self) or not any(self.mapped('l10n_in_b2c_invoice_number')):
            return super()._generate_pos_order_invoice()
        if len(self) != 1:
            raise UserError(self.env._('B2C PoS orders must be invoiced individually. Disable consolidated billing.'))
        if self.is_refund and not self.l10n_in_b2c_invoice_number.startswith('R'):
            raise UserError(self.env._('The B2C invoice number does not match the invoice or credit note type.'))
        if not self.partner_id:
            # Like l10n_es_pos, B2C orders without customer are invoiced to the default customer.
            self.partner_id = self.config_id.default_partner_id
        return super()._generate_pos_order_invoice()

    @api.model
    def _cron_process_pos_orders(self):
        self._l10n_in_process_b2c_orders()
        return super()._cron_process_pos_orders()

    @api.model
    def _l10n_in_process_b2c_orders(self):
        """Invoice the paid B2C orders that have no invoice yet and log the result on each
        order. Orders that already failed are left for the session closing.

        When run by the cron, each order is committed once processed: the orders and
        their session are not kept locked until the end of the cron, e.g. against the
        session closing."""
        domain = self._l10n_in_get_b2c_orders_to_invoice_domain()
        orders = self.search([
            *domain,
            ('message_ids', 'not any', [('message_type', '=', 'auto_comment')]),
        ], order='id')
        odoobot = self.env.ref('base.partner_root')
        from_cron = bool(self.env.context.get('cron_id'))
        if from_cron:
            self.env['ir.cron']._commit_progress(remaining=len(orders))
        for order in orders:
            # Checked again once locked, a session closing may have invoiced it meanwhile.
            if order.try_lock_for_update().filtered_domain(domain):
                if error := order._l10n_in_try_generate_b2c_invoice():
                    _logger.warning('Invoice for PoS order %s could not be posted: %s', order.id, error)
                    body = self.env._('The invoice could not be created: %s', error)
                    # The automated message skips the order in the next runs.
                    message_type = 'auto_comment'
                else:
                    body = self.env._('Invoice %s automatically generated.', order.account_move._get_html_link(title=order.account_move.name))
                    message_type = 'notification'
                order.message_post(body=body, message_type=message_type, author_id=odoobot.id)
            if from_cron and not self.env['ir.cron']._commit_progress(1):
                break

    @api.model
    def _l10n_in_get_b2c_orders_to_invoice_domain(self):
        return [
            ('l10n_in_b2c_invoice_number', '!=', False),
            ('state', '=', 'paid'),
            ('account_move', '=', False),
        ]

    def _l10n_in_try_generate_b2c_invoice(self):
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                self.with_company(self.company_id).with_context(generate_pdf=False)._generate_pos_order_invoice()
        except (UserError, ValidationError) as error:
            return error.args[0]
        return False

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        # Orders paid in the POS UI are numbered by the device. Orders
        # paid elsewhere (self-order, kiosk, platforms, backend) are numbered here.
        if self._is_l10n_in_b2c_order() and not self.l10n_in_b2c_invoice_number:
            sequence = self.config_id._l10n_in_get_b2c_invoice_sequence(self.is_refund)
            self.l10n_in_b2c_invoice_number = self._l10n_in_format_b2c_invoice_number(sequence._next())
        return res

    def action_pos_order_invoice(self):
        # EXTENDS point_of_sale: a B2C order is invoiced again when its customer asks for
        # an invoice on their name.
        if self._is_l10n_in_reinvoice_needed():
            if self.refund_orders_count:
                raise UserError(self.env._(
                    "The order %s has refunds, its B2C invoice cannot be replaced by an invoice on the customer's name.",
                    self.name,
                ))
            self.with_company(self.company_id)._l10n_in_reinvoice()
        return super().action_pos_order_invoice()

    def action_l10n_in_invoice_to_customer(self, partner_id):
        """Invoice the order to the given customer, replacing its B2C invoice, and return
        the action downloading the new invoice."""
        self.ensure_one()
        partner = self.env['res.partner'].browse(partner_id).exists()
        if not partner:
            raise UserError(self.env._('The selected customer no longer exists.'))
        self.partner_id = partner
        self.action_pos_order_invoice()
        return self.action_invoice_download_pdf()

    def _is_l10n_in_default_customer_order(self):
        """Whether the order is a B2C order of the default customer of the PoS, which the
        customer can still have invoiced on their name."""
        self.ensure_one()
        return bool(
            self._is_l10n_in_b2c_order()
            and not self.is_refund
            and self.l10n_in_b2c_invoice_number
            and not self.refund_orders_count
            and self.partner_id == self.config_id.default_partner_id
        )

    def _is_l10n_in_reinvoice_needed(self):
        self.ensure_one()
        return bool(
            self._is_l10n_in_b2c_order()
            and not self.is_refund
            and self.l10n_in_b2c_invoice_number
            and self.account_move
            and self.partner_id.commercial_partner_id != self.account_move.commercial_partner_id
        )

    def _is_l10n_in_b2c_order(self):
        """Indian orders not invoiced on request (B2C) and their refunds get a B2C invoice
        number. Keep in sync with isL10nInB2COrder."""
        self.ensure_one()
        if self.country_code != 'IN' or self.to_invoice:
            return False
        refunded_order = self.refunded_order_id
        # A refund follows its order, which is invoiced on request once re-invoiced.
        return not refunded_order or bool(
            refunded_order.l10n_in_b2c_invoice_number and refunded_order._is_l10n_in_b2c_order()
        )

    # Keep in sync with assignL10nInB2CInvoiceNumber
    def _l10n_in_format_b2c_invoice_number(self, number):
        self.ensure_one()
        prefix = 'R' if self.is_refund else self.config_id.l10n_in_b2c_invoice_prefix
        year_2_digits = str(datetime.now().year)[-2:]

        config_digits = str(self.config_id.id).zfill(2)
        config_identifier = config_digits[-4:] if len(config_digits) >= 4 else config_digits.ljust(4, '0')
        return f'{prefix}{year_2_digits}/{config_identifier}/{str(number).zfill(7)}'

    def _grouping_function(self, line):
        res = super()._grouping_function(line)  # Returns mappingproxy (immutable)
        if self.config_id.company_id.l10n_in_gst_registration_type:
            res = dict(res)  # Convert to mutable dict
            res['l10n_in_hsn_code'] = line.get('l10n_in_hsn_code', '')
            res['product_uom_id'] = line.get('product_uom_id', '')
        return res

    def _prepare_account_move_line_data(self, aggregate=True):
        lines = super()._prepare_account_move_line_data(aggregate)
        if aggregate:
            return lines

        for line in lines:
            move = line.get('account.move.line')
            meta = line.get('metadata')

            if self.config_id.company_id.l10n_in_gst_registration_type and meta:
                pos_line = meta.get('line') if meta else None
                if not pos_line:
                    continue
                move["l10n_in_hsn_code"] = pos_line.l10n_in_hsn_code
                move["product_uom_id"] = pos_line.product_uom_id.id

        return lines

    def _prepare_move_line_vals_from_base_line(self, base_line):
        values = super()._prepare_move_line_vals_from_base_line(base_line)
        if self.config_id.company_id.l10n_in_gst_registration_type:
            values["l10n_in_hsn_code"] = base_line.get("l10n_in_hsn_code", "")
            values["product_uom_id"] = base_line.get("product_uom_id", "").id
        return values

    def _l10n_in_reinvoice(self):
        """Replace the B2C invoice of the order by an invoice on the name of its customer.

        1. Unreconcile the B2C invoice from the payments of the order, which keeps those
           payments open on the receivable of the B2C (default) customer.
        2. Cancel the B2C invoice by a credit note and create the B2B invoice for the
           customer, as the "Reverse > Full refund and new draft invoice" action does.
        3. Move the payments from the B2C customer to the B2B invoice with a transfer
           entry, so that the B2B invoice is paid without registering the payments again.
        """
        self.ensure_one()
        if not self.env['res.company']._with_locked_records(self, allow_raising=False):
            raise UserError(self.env._('This order is already being invoiced. Please try again later.'))
        b2c_invoice = self.account_move
        payment_lines = b2c_invoice._l10n_in_detach_payment_lines()
        b2b_invoice = self._l10n_in_replace_invoice(b2c_invoice)
        if payment_lines:
            self._l10n_in_transfer_payment_lines(payment_lines, b2b_invoice)

        credit_note = b2c_invoice.reversal_move_ids
        self.message_post(body=self.env._(
            'Invoice %(b2c_invoice)s cancelled by the credit note %(credit_note)s and replaced by %(b2b_invoice)s for %(customer)s.',
            b2c_invoice=b2c_invoice._get_html_link(title=b2c_invoice.name),
            credit_note=credit_note._get_html_link(title=credit_note.name),
            b2b_invoice=b2b_invoice._get_html_link(title=b2b_invoice.name),
            customer=self.partner_id.display_name,
        ))

    def _l10n_in_replace_invoice(self, b2c_invoice):
        self.ensure_one()
        today = fields.Date.context_today(self)
        reversal = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=b2c_invoice.ids,
        ).create({'date': today, 'journal_id': b2c_invoice.journal_id.id})
        reversal.modify_moves()
        b2b_invoice = reversal.new_move_ids
        b2b_invoice.write({
            'partner_id': self.partner_id.address_get(['invoice'])['invoice'],
            'invoice_date': today,
        })
        # Invoiced on request from now on: no more a B2C order, nor its refunds.
        self.write({'to_invoice': True, 'account_move': b2b_invoice.id})
        b2b_invoice.with_context(**self._get_invoice_post_context())._post()
        return b2b_invoice

    def _l10n_in_transfer_payment_lines(self, payment_lines, b2b_invoice):
        self.ensure_one()
        term_lines = b2b_invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        transfer = self.env['account.move'].sudo().with_context(skip_invoice_sync=True).create({
            'move_type': 'entry',
            'company_id': self.company_id.id,
            'journal_id': self.config_id.closing_journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.env._('Payments of %(order)s moved to %(b2b_invoice)s', order=self.name, b2b_invoice=b2b_invoice.name),
            'line_ids': [
                Command.create({
                    'name': line.name,
                    'account_id': line.account_id.id,
                    'partner_id': line.partner_id.id,
                    'balance': -line.balance,
                })
                for line in payment_lines
            ] + [
                Command.create({
                    'name': b2b_invoice.name,
                    'account_id': term_lines[0].account_id.id,
                    'partner_id': b2b_invoice.commercial_partner_id.id,
                    'balance': sum(payment_lines.mapped('balance')),
                }),
            ],
        })
        transfer._post()
        for payment_line, transfer_line in zip(payment_lines, transfer.line_ids[:-1]):
            (payment_line | transfer_line).reconcile()
        (term_lines | transfer.line_ids[-1]).reconcile()
