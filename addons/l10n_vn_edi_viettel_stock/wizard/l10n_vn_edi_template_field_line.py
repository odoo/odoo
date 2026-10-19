# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nVnEdiTemplateFieldLine(models.TransientModel):
    _name = 'l10n_vn_edi_viettel_stock.template_field_line'
    _description = 'Template Field Line for SInvoice Transfer Note'

    wizard_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel_stock.send_wizard',
        required=True,
        ondelete='cascade',
    )
    key_tag = fields.Char(
        string='Key Tag',
        required=True,
        export_string_translation=False,
    )
    key_label = fields.Char(
        string='Field',
        required=True,
    )
    value = fields.Char(string='Value')
    value_type = fields.Char(
        string='Value Type',
        default='text',
        export_string_translation=False,
    )
    is_required = fields.Boolean(
        string='Required',
        export_string_translation=False,
    )
    is_seller = fields.Boolean(
        string='Is Seller',
        export_string_translation=False,
    )
