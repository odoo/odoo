# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    salesman_as_agent = fields.Boolean(
        string="Convert salesman into agent",
        help="If the user linked to this partner is put as salesman and no "
        "other commission rule is triggered, this agent will be "
        "added as the commission agent",
    )

    @api.constrains("salesman_as_agent", "commission_id")
    def _check_salesman_as_agent(self):
        for record in self:
            if record.salesman_as_agent and not record.commission_id:
                raise exceptions.ValidationError(
                    _("You can't have a salesman auto-agent without commission.")
                )
