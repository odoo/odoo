# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10nBrNCMCode(models.Model):
    _name = "l10n_br.ncm.code"
    _description = "NCM Code"

    code = fields.Char("Code")
    name = fields.Char("Name")

    def init(self):
        """Set all records to noupdate on module update so they can be edited by the user.
        TODO: remove this in master and do it in post_init_hook instead."""
        res = super().init()
        xml_ids = self.env["ir.model.data"].search(
            [
                ("module", "in", ("l10n_br_avatax", "l10n_br_avatax_services")),
                ("model", "=", self._name),
                ("noupdate", "=", False),
            ]
        )
        xml_ids.write({"noupdate": True})
        return res
