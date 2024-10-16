from odoo import models
from odoo.addons import web, mail


class IrUiMenu(web.IrUiMenu, mail.IrUiMenu):

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not any(company.check_account_audit_trail for company in self.env.user.company_ids):
            res.append(self.env.ref('account.account_audit_trail_menu').id)
        return res
