from odoo import models, fields


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    l10n_pt_tax_exemption_reason = fields.Many2one(
        comodel_name='l10n.pt.tax.exemption.reason',
        string="Tax exemption reason",
        help="Reason why we may exempt an item sale from any tax",
        groups='account.group_account_invoice')
