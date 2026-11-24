# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortalLoyalty(CustomerPortal):
    @route()
    def counters(self, counters, **kw):
        values = super().counters(counters, **kw)
        if not counters:
            # we want those data to be added to the /my/home page only, and always computed
            values["cards_per_programs"] = dict(
                self
                .env["loyalty.card"]
                .sudo()
                ._read_group(
                    domain=[
                        ("partner_id", "=", self.env.user.partner_id.id),
                        ("program_id.active", "=", True),
                        ("program_id.program_type", "in", ["loyalty", "ewallet"]),
                        "|",
                        ("expiration_date", ">=", fields.Date.context_today(request.env.user)),
                        ("expiration_date", "=", False),
                    ],
                    groupby=["program_id"],
                    aggregates=["id:recordset"],
                )
            )
        return values

    @route("/my/loyalty_card/<int:card_id>/values", type="jsonrpc", auth="user")
    def portal_get_card_values(self, card_id):
        """Retrieve card values for portal card dialog.

        :param card_id(str): The ID of the loyalty card.
        :return(dict): A dictionary with card values.
        """
        card_sudo = (
            self
            .env["loyalty.card"]
            .sudo()
            .search([("id", "=", int(card_id)), ("partner_id", "=", self.env.user.partner_id.id)])
        )
        if not card_sudo:
            return {}

        program_type = card_sudo.program_id.program_type
        return {
            "card": {
                "id": card_sudo.id,
                "points_display": card_sudo.points_display,
                "expiration_date": card_sudo.expiration_date,
                "code": card_sudo.code,
            },
            "program": {"program_name": card_sudo.program_id.name, "program_type": program_type},
        }
