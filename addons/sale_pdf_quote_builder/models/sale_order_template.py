from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"
    _check_company_auto = True

    quotation_document_ids = fields.Many2many(
        comodel_name="quotation.document",
        relation="header_footer_quotation_template_rel",
        string="Headers and footers",
        check_company=True,
    )
