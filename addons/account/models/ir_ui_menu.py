from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        hide_audit_menu = not any(company.check_account_audit_trail for company in self.env.user.company_ids)
        if hide_audit_menu:
            audit_menu = self.env.ref('account.account_audit_trail_menu', raise_if_not_found=False)
            if audit_menu:
                res.append(audit_menu.id)
        return res
