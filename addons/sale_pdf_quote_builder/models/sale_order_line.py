# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    available_product_document_ids = fields.Many2many(
        string="Available Product Documents",
        comodel_name='product.document',
        relation='available_sale_order_line_product_document_rel',
        compute='_compute_available_product_document_ids',
    )
    product_document_ids = fields.Many2many(
        string="Product Documents",
        help="The product documents for this order line that will be merged in the PDF quote.",
        comodel_name='product.document',
        relation='sale_order_line_product_document_rel',
        domain="[('id', 'in', available_product_document_ids)]",
        compute='_compute_product_document_ids',
        store=True,
        readonly=False,
    )

    # === COMPUTE METHODS === #

    def _compute_available_product_document_ids(self):
        for line in self:
            line.available_product_document_ids = self.env['product.document'].search([
                '|',
                    '&',
                        ('res_model', '=', 'product.product'),
                        ('res_id', '=', line.product_id.id),
                    '&',
                        ('res_model', '=', 'product.template'),
                        ('res_id', '=', line.product_template_id.id),
                ('attached_on_sale', '=', 'inside')
            ], order='res_model, sequence').ids

    @api.depends('order_id.is_pdf_quote_builder_active', 'product_id')
    def _compute_product_document_ids(self):
        """ Compute the first eligible product document for this SOL when the feature is active. """
        for line in self:
            if not line.order_id.is_pdf_quote_builder_active or not line.product_id:
                line.product_document_ids = self.env['product.document']
            else:
                default_docs = line.product_id.product_document_ids.filtered(
                    lambda d: d.attached_on_sale == 'inside'
                )
                if not default_docs:
                    default_docs = line.product_template_id.product_document_ids.filtered(
                        lambda d: d.attached_on_sale == 'inside'
                    )
                if default_docs:
                    line.product_document_ids = [default_docs[0].id]
                else:
                    line.product_document_ids = self.env['product.document']
