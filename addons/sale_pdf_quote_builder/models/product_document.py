# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.sale_pdf_quote_builder import utils


class ProductDocument(models.Model):
    _inherit = 'product.document'

    attached_on_sale = fields.Selection(
        selection_add=[('inside', "Inside quote pdf")],
        help="Allows you to share the document with your customers within a sale.\n"
             "Leave it empty if you don't want to share this document with sales customer.\n"
             "On quote: the document will be sent to and accessible by customers at any time.\n"
             "e.g. this option can be useful to share Product description files.\n"
             "On order confirmation: the document will be sent to and accessible by customers.\n"
             "e.g. this option can be useful to share User Manual or digital content bought on"
             " ecommerce. \n"
             "Inside quote: The document will be included in the pdf of the quotation and sale"
             " order between the header pages and the quote table. ",
        ondelete={'inside': 'set default'},
    )
    form_field_ids = fields.Many2many(
        string="Form Fields Included",
        comodel_name='sale.pdf.form.field',
        domain=[('document_type', '=', 'product_document')],
        compute='_compute_form_field_ids',
        store=True,
    )

    # === CONSTRAINT METHODS ===#

    @api.constrains('attached_on_sale', 'datas', 'type')
    def _check_attached_on_and_datas_compatibility(self):
        for doc in self.filtered(lambda doc: doc.attached_on_sale == 'inside'):
            if doc.type != 'binary':
                raise ValidationError(_(
                    "When attached inside a quote, the document must be a file, not a URL."
                ))
            if doc.datas and not doc.mimetype.endswith('pdf'):
                raise ValidationError(_("Only PDF documents can be attached inside a quote."))
            if doc.datas:
                utils._ensure_document_not_encrypted(base64.b64decode(doc.datas))

    # === COMPUTE METHODS === #

    @api.depends('datas', 'attached_on_sale')
    def _compute_form_field_ids(self):
        # Empty the linked form fields as we want all and only those from the current datas
        self.form_field_ids = [Command.clear()]
        document_to_parse = self.filtered(
            lambda doc: doc.attached_on_sale == 'inside' and doc.datas and doc.mimetype and doc.mimetype.endswith('pdf')
        )
        if document_to_parse:
            doc_type = 'product_document'
            self.env['sale.pdf.form.field']._create_or_update_form_fields_on_pdf_records(
                document_to_parse, doc_type
            )

    # === ACTION METHODS ===#

    def action_open_pdf_form_fields(self):
        self.ensure_one()
        return {
            'name': _('Form Fields'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.pdf.form.field',
            'view_mode': 'list',
            'context': {
                'default_document_type': 'product_document',
                'default_product_document_ids': self.id,
                'default_quotation_document_ids': False,
                'search_default_context_document': True,
            },
            'target': 'current',
        }
