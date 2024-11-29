# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'
    _check_company_auto = True

    quotation_document_ids = fields.Many2many(
        string="Headers and footers",
        comodel_name='quotation.document',
        relation='header_footer_quotation_template_rel',
        check_company=True,
    )
