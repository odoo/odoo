# Copyright 2023 Ecosoft (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def _server_action_tier(self, reviews, status):
        for review in reviews:
            if status == "approved":
                server_action = review.definition_id.server_action_id
            if status == "rejected":
                server_action = review.definition_id.rejected_server_action_id
            server_action_tier = self.env.context.get("server_action_tier")
            # Don't allow reentrant server action as it will lead to
            # recursive behaviour
            if server_action and (
                not server_action_tier or server_action_tier != server_action.id
            ):
                server_action.with_context(
                    server_action_tier=server_action.id,
                    active_model=self._name,
                    active_id=self.id,
                ).sudo().run()

    def _validate_tier(self, tiers=False):
        self.ensure_one()
        res = super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(lambda l: l.status == "approved")
        self._server_action_tier(reviews, "approved")
        return res

    def _rejected_tier(self, tiers=False):
        self.ensure_one()
        res = super()._rejected_tier(tiers)
        reviews = self.review_ids.filtered(lambda l: l.status == "rejected")
        self._server_action_tier(reviews, "rejected")
        return res
