from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    lc_journal_id = fields.Many2one(comodel_name="account.journal")
