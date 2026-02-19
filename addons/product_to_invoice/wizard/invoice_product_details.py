# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Jabin MP (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InvoiceProductDetails(models.TransientModel):
    """ Wizard model to display invoice product details."""
    _name = 'invoice.product.details'
    _description = 'Invoice Product Details'

    product_id = fields.Many2one('product.product', string='Product',
                                 readonly=True,
                                 help="Select the product for this record.")
    qty = fields.Float(string='Quantity', default=1,
                       help="Enter the quantity of the selected product.")
    account_move_id = fields.Many2one('account.move', readonly=True,
                                      help="Link to the corresponding "
                                           "account move.")
    price_unit = fields.Float(string='Unit Price',
                              help="Enter the unit price of the product.")
    invoice_history_ids = fields.One2many('product.invoice.history',
                                          'product_details_id', readonly=True,
                                          help="History of invoices related"
                                               " to this product.")
    date_from = fields.Date(default=fields.Date.today() - timedelta(days=30),
                            help="Default date from which a record is "
                                 "created.")
    limit = fields.Integer(string='Limit', default=20,
                           help="Set the limit for product")

    @api.onchange('date_from', 'limit')
    def _onchange_date_from(self):
        """Update invoice history based on selected date range and limit.
        This method is triggered when the 'date_from' or 'limit' field changes.
        It retrieves invoice lines matching the specified criteria and
         updates the invoice history. """
        invoice_lines = self.env['account.move.line'].search([
            ('product_id', '=', self.product_id.id),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.move_type', 'in', ('out_invoice', 'in_invoice'))
        ], limit=self.limit)
        vals = [(5, 0, 0)]
        for line in invoice_lines:
            vals.append((0, 0, {
                'date': line.move_id.invoice_date,
                'partner_id': line.move_id.partner_id.id,
                'qty': line.quantity,
                'account_move_number': line.move_id.name,
                'price_unit': line.price_unit,
                'total': line.price_subtotal,
                'type': line.move_id.move_type,
                'move_id': line.move_id.id
            }))
        self.invoice_history_ids = vals

    def action_add_to_invoice(self):
        """Add the product to the invoice.
         This method is used to add the current product to the associated
         invoice.It creates an invoice line and adds it to the invoice."""
        account_id = self.product_id._get_invoice_account(self.account_move_id)
        tax_ids = self.product_id._get_invoice_taxes \
            (self.account_move_id, account_id)
        invoice_line_vals = {
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'quantity': self.qty,
            'price_unit': self.price_unit,
            'account_id': account_id.id,
            'tax_ids': tax_ids,
            'move_id': self.account_move_id.id,
        }
        invoice_line = self.env['account.move.line'].create(invoice_line_vals)
        if invoice_line:
            self.account_move_id.write(
                {'invoice_line_ids': [(4, invoice_line.id)]})
        else:
            raise UserError(_("Failed to create invoice line."))
