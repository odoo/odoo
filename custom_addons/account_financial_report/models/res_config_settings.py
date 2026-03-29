# Copyright 2023 Tecnativa - Carolina Fernandez
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    age_partner_config_id = fields.Many2one(
        "account.age.report.configuration",
        string="Intervals configuration",
    )

    def set_values(self):
        self.env["ir.default"].sudo().set(
            "aged.partner.balance.report.wizard",
            "age_partner_config_id",
            self.age_partner_config_id.id,
            company_id=self.env.company.id,
        )
        return super().set_values()

    @api.model
    def get_values(self):
        res = super().get_values()
        res.update(
            age_partner_config_id=self.env["ir.default"]
            .sudo()
            ._get(
                "aged.partner.balance.report.wizard",
                "age_partner_config_id",
                company_id=self.env.company.id,
            )
        )
        return res
