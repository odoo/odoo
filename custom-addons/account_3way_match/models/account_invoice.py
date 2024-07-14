# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare
from odoo.tools.sql import column_exists, create_column

# Available values for the release_to_pay field.
_release_to_pay_status_list = [('yes', 'Yes'), ('no', 'No'), ('exception', 'Exception')]

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "release_to_pay"):
            # Create column manually to set default value to 'exception' on postgres level.
            # This way we avoid heavy computation on module installation.
            self.env.cr.execute("ALTER TABLE account_move ADD COLUMN release_to_pay VARCHAR DEFAULT 'exception'")

        return super()._auto_init()

    release_to_pay = fields.Selection(
        _release_to_pay_status_list,
        compute='_compute_release_to_pay',
        copy=False,
        store=True,
        help="This field can take the following values :\n"
             "  * Yes: you should pay the bill, you have received the products\n"
             "  * No, you should not pay the bill, you have not received the products\n"
             "  * Exception, there is a difference between received and billed quantities\n"
             "This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.")
    release_to_pay_manual = fields.Selection(
        _release_to_pay_status_list,
        string='Should Be Paid',
        compute='_compute_release_to_pay_manual', store='True', readonly=False,
        help="  * Yes: you should pay the bill, you have received the products\n"
             "  * No, you should not pay the bill, you have not received the products\n"
             "  * Exception, there is a difference between received and billed quantities\n"
             "This status is defined automatically, but you can force it by ticking the 'Force Status' checkbox.")
    force_release_to_pay = fields.Boolean(
        string="Force Status",
        help="Indicates whether the 'Should Be Paid' status is defined automatically or manually.")

    @api.depends('invoice_line_ids.can_be_paid', 'force_release_to_pay', 'payment_state')
    def _compute_release_to_pay(self):
        records = self
        if self.env.context.get('module') == 'account_3way_match':
            # on module installation we set 'no' for all paid bills and other non relevant records at once
            records = records.filtered(lambda r: r.payment_state != 'paid' and r.move_type in ('in_invoice', 'in_refund'))
            (self - records).release_to_pay = 'no'
        for invoice in records:
            if invoice.payment_state == 'paid' or not invoice.is_invoice(include_receipts=True):
                # no need to pay, if it's already paid
                invoice.release_to_pay = 'no'
            elif invoice.force_release_to_pay:
                #we must use the manual value contained in release_to_pay_manual
                invoice.release_to_pay = invoice.release_to_pay_manual
            else:
                #otherwise we must compute the field
                result = None
                for invoice_line in invoice.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
                    line_status = invoice_line.can_be_paid
                    if line_status == 'exception':
                        #If one line is in exception, the entire bill is
                        result = 'exception'
                        break
                    elif not result:
                        result = line_status
                    elif line_status != result:
                        result = 'exception'
                        break
                    #The last two elif conditions model the fact that a
                    #bill will be in exception if its lines have different status.
                    #Otherwise, its status will be the one all its lines share.

                #'result' can be None if the bill was entirely empty.
                invoice.release_to_pay = result or 'no'

    @api.depends('release_to_pay', 'force_release_to_pay')
    def _compute_release_to_pay_manual(self):
        for invoice in self:
            if not (invoice.payment_state == 'paid' or not invoice.is_invoice(include_receipts=True) or invoice.force_release_to_pay):
                invoice.release_to_pay_manual = invoice.release_to_pay

    @api.onchange('release_to_pay_manual')
    def _onchange_release_to_pay_manual(self):
        if self.release_to_pay and self.release_to_pay_manual != self.release_to_pay:
            self.force_release_to_pay = True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move_line", "can_be_paid"):
            # Create column manually to set default value to 'exception' on postgres level.
            # This way we avoid heavy computation on module installation.
            self.env.cr.execute("ALTER TABLE account_move_line ADD COLUMN can_be_paid VARCHAR DEFAULT 'exception'")

        return super()._auto_init()


    @api.depends('purchase_line_id.qty_received', 'purchase_line_id.qty_invoiced', 'purchase_line_id.product_qty', 'price_unit')
    def _can_be_paid(self):
        """ Computes the 'release to pay' status of an invoice line, depending on
        the invoicing policy of the product linked to it, by calling the dedicated
        subfunctions. This function also ensures the line is linked to a purchase
        order (otherwise, can_be_paid will be set as 'exception'), and the price
        between this order and the invoice did not change (otherwise, again,
        the line is put in exception).
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for invoice_line in self:
            po_line = invoice_line.purchase_line_id
            if po_line:
                invoiced_qty = po_line.qty_invoiced
                received_qty = po_line.qty_received
                ordered_qty = po_line.product_qty

                # A price difference between the original order and the invoice results in an exception
                invoice_currency = invoice_line.currency_id
                order_currency = po_line.currency_id
                invoice_converted_price = invoice_currency._convert(
                    invoice_line.price_unit, order_currency, invoice_line.company_id, fields.Date.today())
                if order_currency.compare_amounts(po_line.price_unit, invoice_converted_price) != 0:
                    invoice_line.can_be_paid = 'exception'
                    continue

                if po_line.product_id.purchase_method == 'purchase': # 'on ordered quantities'
                    invoice_line._can_be_paid_ordered_qty(invoiced_qty, received_qty, ordered_qty, precision)
                else: # 'on received quantities'
                    invoice_line._can_be_paid_received_qty(invoiced_qty, received_qty, ordered_qty, precision)

            else: # Serves as default if the line is not linked to any Purchase.
                invoice_line.can_be_paid = 'exception'

    def _can_be_paid_ordered_qty(self, invoiced_qty, received_qty, ordered_qty, precision):
        """
        Gives the release_to_pay status of an invoice line for 'on ordered
        quantity' billing policy, if this line's invoice is related to a purchase order.

        This function sets can_be_paid field to one of the following:
        'yes': the content of the line has been ordered and can be invoiced
        'no' : the content of the line hasn't been ordered at all, and cannot be invoiced
        'exception' : only part of the invoice has been ordered
        """
        if float_compare(invoiced_qty - self.quantity, ordered_qty, precision_digits=precision) >= 0:
            self.can_be_paid = 'no'
        elif float_compare(invoiced_qty, ordered_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'yes'
        else:
            self.can_be_paid = 'exception'

    def _can_be_paid_received_qty(self, invoiced_qty, received_qty, ordered_qty, precision):
        """
        Gives the release_to_pay status of an invoice line for 'on received
        quantity' billing policy, if this line's invoice is related to a purchase order.

        This function sets can_be_paid field to one of the following:
        'yes': the content of the line has been received and can be invoiced
        'no' : the content of the line hasn't been received at all, and cannot be invoiced
        'exception' : ordered and received quantities differ
        """
        if float_compare(invoiced_qty, received_qty, precision_digits=precision) <= 0:
            self.can_be_paid = 'yes'
        elif received_qty == 0 and float_compare(invoiced_qty, ordered_qty, precision_digits=precision) <= 0: # "and" part to ensure a too high billed quantity results in an exception:
            self.can_be_paid = 'no'
        else:
            self.can_be_paid = 'exception'

    can_be_paid = fields.Selection(
        _release_to_pay_status_list,
        compute='_can_be_paid',
        copy=False,
        store=True,
        string='Release to Pay')
