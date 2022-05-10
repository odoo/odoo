from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"
    l10n_pt_original_html_body = fields.Text("Original HTML body of the account move", translate=False)
