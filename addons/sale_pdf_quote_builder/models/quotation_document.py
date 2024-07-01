# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.sale_pdf_quote_builder import utils


class QuotationDocument(models.Model):
    _name = "quotation.document"
    _description = "Quotation's Headers & Footers"
    _inherits = {
        'ir.attachment': 'ir_attachment_id',
    }
    _order = 'document_type desc, sequence, name'

    ir_attachment_id = fields.Many2one(
        'ir.attachment',
        string="Related attachment",
        required=True,
        ondelete='cascade'
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[('header', "Header"), ('footer', "Footer")],
        default='header',
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the header or footer without removing it."
    )
    sequence = fields.Integer(default=10)
    quotation_template_ids = fields.Many2many(
        string="Quotation Templates",
        comodel_name='sale.order.template',
        relation='header_footer_quotation_template_rel'
    )

    @api.constrains('datas')
    def _check_pdf_validity(self):
        for doc in self:
            if doc.datas and not doc.mimetype.endswith('pdf'):
                raise ValidationError(_("Only PDF documents can be used as header or footer."))
            utils._ensure_document_not_encrypted(base64.b64decode(doc.datas))

    # === ACTION METHODS ===#

    def action_open_dynamic_fields_configurator_wizard(self):
        self.ensure_one()
        default_form_fields = {'header_footer': list(utils._get_valid_form_fields(self.datas))}
        return {
            'name': _("Whitelist PDF Fields"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.pdf.quote.builder.dynamic.fields.wizard',
            'target': 'new',
            'context': {'default_current_form_fields': json.dumps(default_form_fields)},
        }
