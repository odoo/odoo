from odoo import api, models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        domain = [("to_buy", "=", False)] + domain
        return super().search(domain, offset, limit, order)
