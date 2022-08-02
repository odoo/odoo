from odoo import models

class ResPartner(models.Model):
    _inherit = "res.partner"

    def _l10n_th_get_branch_name(self, use_code=False):
        if not self.is_company:
            return ""
        code = self.company_registry or ""
        return "Branch " + code if code else "Headquarter"
