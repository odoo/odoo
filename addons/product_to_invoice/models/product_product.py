# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Jabin MP(<https://www.cybrosys.com>)
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
from odoo import api, fields, models


class ProductProduct(models.Model):
    """This class extends the 'product.product' model in Odoo and adds
       additional functionalities related to invoice handling."""
    _inherit = 'product.product'

    @api.depends_context('add_to_invoice')
    def _compute_add_to_invoice(self):
        """Compute the 'add_to_invoice' field based on the context.
        The 'add_to_invoice' field is set to True when the context
        variable 'add_to_invoice' is present and has a truthy value.
        Otherwise, it is set to False."""
        for record in self:
            record.add_to_invoice = bool(self.env.context.get('add_to_invoice')
                                         )
    add_to_invoice = fields.Boolean(
        string='Add to Invoice',
        compute='_compute_add_to_invoice',
        help='Whether to show the "Add to Invoice" button in the tree view.')

    def _get_invoice_taxes(self, move_id, account_id):
        """Get invoice taxes based on move type and account."""
        self.ensure_one()
        tax_ids = self.taxes_id.filtered(
            lambda tax: tax.company_id == move_id.company_id) if \
            move_id.move_type == 'out_invoice' else \
            self.supplier_taxes_id.filtered(
                lambda tax: tax.company_id == move_id.company_id) if \
                move_id.move_type == 'in_invoice' else \
                account_id.tax_ids
        if not tax_ids:
            tax_ids = move_id.company_id.account_sale_tax_id if \
                move_id.move_type == 'out_invoice' else \
                move_id.company_id.account_purchase_tax_id if \
                    move_id.move_type == 'in_invoice' else \
                    self.env['account.tax']
        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id ==
                                                   self.company_id)
        return tax_ids

    def _get_invoice_account(self, move_id):
        """Return the income/expense account of the selected product."""
        self.ensure_one()
        self = self.with_company(move_id.journal_id.company_id)
        accounts = self.product_tmpl_id.get_product_accounts \
            (fiscal_pos=move_id.fiscal_position_id)
        return accounts['income'] if move_id.move_type == 'out_invoice' \
            else accounts['expense']

    def action_add_to_invoice(self):
        """Add the product to the invoice.
        This method is triggered when the "Add to Invoice" button is clicked.
        It creates an invoice line and adds it to the invoice."""
        invoice_id = self.env['account.move']. \
            browse(self._context.get('active_id'))
        account_id = self._get_invoice_account(invoice_id)
        tax_ids = self._get_invoice_taxes(invoice_id, account_id)
        invoice_line_vals = {
            'product_id': self.id,
            'product_uom_id': self.uom_id.id,
            'quantity': 1,
            'price_unit': self.lst_price if invoice_id.move_type ==
                                            'out_invoice'
            else self.standard_price,
            'account_id': account_id.id,
            'tax_ids': [(6, 0, tax_ids.ids)]
        }
        invoice_id.write({
            'invoice_line_ids': [(0, 0, invoice_line_vals)]
        })

    def action_change_qty(self):
        """Open the product details wizard.
        This method is triggered when the "Change Qty" button is clicked.
        It opens a wizard to modify the quantity and other details of
        the product. """
        invoice_id = self.env['account.move'] \
            .browse(self._context.get('active_id'))
        return {
            'name': 'Product Details',
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.product.details',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_move_id': invoice_id.id,
                'default_product_id': self.id,
                'default_price_unit': self.lst_price if invoice_id.move_type
                                                        == 'out_invoice'
                else self.standard_price,
            },
        }
