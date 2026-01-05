from odoo import models, tools


class ResCompany(models.Model):
    _inherit = "res.company"

    @tools.ormcache("payment_type")
    def _get_bundle_journal(self, payment_type: str) -> int:
        if payment_type == "inbound":
            return (
                self.env["account.journal"]
                .search([("inbound_payment_method_line_ids.payment_method_id.code", "=", "payment_bundle"), ('company_id', '=', self.id)])
                .id
            )
        else:
            return (
                self.env["account.journal"]
                .search([("inbound_payment_method_line_ids.payment_method_id.code", "=", "payment_bundle"), ('company_id', '=', self.id)])
                .id
            )
