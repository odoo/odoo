from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"
    l10n_pt_original_pdf = fields.Binary("Original PDF", attachment=False)
    l10n_pt_duplicate_pdf = fields.Binary("Duplicate PDF", attachment=False)
