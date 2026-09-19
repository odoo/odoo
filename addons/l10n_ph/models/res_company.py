from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "branch_code",
        "l10n_ph_rdo",
    )
