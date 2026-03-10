# Copyright 2019 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Uom(models.Model):
    _name = "uom.uom"
    _inherit = ["uom.uom", "mail.thread", "mail.activity.mixin"]

    code = fields.Char(size=6)

    alternative_ids = fields.One2many(
        comodel_name="uom.uom.alternative",
        inverse_name="uom_id",
        string="Alternative names",
    )

    def _get_code_domain(self, sub_domain, domain):
        code_operator = sub_domain[1]
        code_value = sub_domain[2]
        alternative = (
            self.env["uom.uom.alternative"]
            .search([("code", code_operator, code_value)])
            .mapped("uom_id")
        )
        domain = [
            ("id", "in", alternative.ids)
            if x[0] == "code" and x[2] == code_value and alternative.ids
            else x
            for x in domain
        ]
        return domain

    @api.model
    def search(self, domain, *args, **kwargs):
        for sub_domain in list(filter(lambda x: x[0] == "code", domain)):
            domain = self._get_code_domain(sub_domain, domain)
        return super().search(domain, *args, **kwargs)
