from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = ("l10n_no_bronnoysund_number",)
