# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    available_product_document_ids = fields.Many2many(
        string="Available Product Documents",
        comodel_name='product.document',
        relation='available_sale_order_line_product_document_rel',
        compute='_compute_available_product_document_ids',
        compute_sudo=True, # To access attached_on_sale
    )
    product_document_ids = fields.Many2many(
        string="Product Documents",
        help="The product documents for this order line that will be merged in the PDF quote.",
        comodel_name='product.document',
        relation='sale_order_line_product_document_rel',
        domain="[('id', 'in', available_product_document_ids)]",
        readonly=False,
    )

    # === ONCHANGE METHODS === #

    @api.onchange('product_id', 'product_template_id')
    def _onchange_product(self):
        for line in self:
            # Ensure selected documents are still in the available documents
            line.product_document_ids = line.product_document_ids.filtered(
                lambda doc: doc in line.available_product_document_ids
            )

    # === COMPUTE METHODS === #

    @api.depends('product_id', 'product_template_id')
    def _compute_available_product_document_ids(self):
        available_documents_ordered = self.env['product.document']._read_group(
            [
                ('attached_on_sale', '=', 'inside'),
                '|',
                    '&',
                        ('res_model', '=', 'product.product'),
                        ('res_id', 'in', self.product_id.ids),
                    '&',
                        ('res_model', '=', 'product.template'),
                        ('res_id', 'in', self.product_template_id.ids),
            ],
            ['res_model', 'res_id', 'sequence'],
            ['id:array_agg'],
            order='res_model, sequence',
        )
        available_documents = defaultdict(list)
        for res_model, res_id, _sequence, ids in available_documents_ordered:
            available_documents[res_model, res_id].extend(ids)
        for line in self:
            line.available_product_document_ids = (
                available_documents['product.product', line.product_id.id]
                + available_documents['product.template', line.product_template_id.id]
            )
