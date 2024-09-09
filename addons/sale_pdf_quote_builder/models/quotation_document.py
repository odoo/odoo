# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.sale_pdf_quote_builder import utils


class QuotationDocument(models.Model):
    _name = 'quotation.document'
    _description = "Quotation's Headers & Footers"
    _inherits = {
        'ir.attachment': 'ir_attachment_id',
    }
    _order = 'document_type desc, sequence, name'

    ir_attachment_id = fields.Many2one(
        string="Related attachment",
        comodel_name='ir.attachment',
        ondelete='cascade',
        required=True,
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[('header', "Header"), ('footer', "Footer")],
        required=True,
        default='header',
    )
    active = fields.Boolean(
        help="If unchecked, it will allow you to hide the header or footer without removing it.",
        default=True,
    )
    sequence = fields.Integer(default=10)
    quotation_template_ids = fields.Many2many(
        string="Quotation Templates",
        comodel_name='sale.order.template',
        relation='header_footer_quotation_template_rel',
    )
    form_field_ids = fields.Many2many(
        string="Form Fields Included",
        comodel_name='sale.pdf.form.field',
        domain=[('document_type', '=', 'quotation_document')],
        compute='_compute_form_field_ids',
        store=True,
    )

    # === CONSTRAINT METHODS ===#

    @api.constrains('datas')
    def _check_pdf_validity(self):
        for doc in self:
            if doc.datas and not doc.mimetype.endswith('pdf'):
                raise ValidationError(_("Only PDF documents can be used as header or footer."))
            utils._ensure_document_not_encrypted(base64.b64decode(doc.datas))

    # === COMPUTE METHODS === #

    @api.depends('datas')
    def _compute_form_field_ids(self):
        # Empty the linked form fields as we want all and only those from the current datas
        self.form_field_ids = [Command.clear()]
        document_to_parse = self.filtered(lambda doc: doc.datas)
        if document_to_parse:
            doc_type = 'quotation_document'
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
                'default_document_type': 'quotation_document',
                'default_product_document_ids': False,
                'default_quotation_document_ids': self.id,
                'search_default_context_document': True,
            },
            'target': 'current',
        }
