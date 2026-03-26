from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    gov_auditoria_access_expiration = fields.Date(
        string="Auditoria Access Expiration",
        help="Optional expiration date for temporary auditor read-only access.",
    )
