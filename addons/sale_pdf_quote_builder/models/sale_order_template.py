# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    quotation_document_ids = fields.Many2many(
        string="Headers and footers",
        comodel_name='quotation.document',
        relation='header_footer_quotation_template_rel',
    )
    sale_header_ids = fields.Many2many(
        string="Headers",
        comodel_name='quotation.document',
        domain=[('document_type', '=', 'header')],
        compute='_compute_sale_header_and_sale_footer_ids',
        inverse='_inverse_sale_header_and_sale_footer_ids',
    )
    sale_footer_ids = fields.Many2many(
        string="Footers",
        comodel_name='quotation.document',
        domain=[('document_type', '=', 'footer')],
        compute='_compute_sale_header_and_sale_footer_ids',
        inverse='_inverse_sale_header_and_sale_footer_ids',
    )

    # === COMPUTE METHODS === #

    def _compute_sale_header_and_sale_footer_ids(self):
        for template in self:
            template.sale_header_ids = template.quotation_document_ids.filtered(
                lambda doc: doc.document_type == 'header'
            ).ids
            template.sale_footer_ids = template.quotation_document_ids.filtered(
                lambda doc: doc.document_type == 'footer'
            ).ids

    def _inverse_sale_header_and_sale_footer_ids(self):
        for template in self:
            quotation_documents = template.sale_header_ids + template.sale_footer_ids
            template.quotation_document_ids = quotation_documents.ids
