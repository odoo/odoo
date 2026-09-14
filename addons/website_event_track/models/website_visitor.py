from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    event_track_visitor_ids = fields.One2many(
        comodel_name="event.track.visitor",
        inverse_name="visitor_id",
        string="Track Visitors",
        groups="event.group_event_user",
    )
    event_track_wishlisted_ids = fields.Many2many(
        comodel_name="event.track",
        string="Wishlisted Tracks",
        compute="_compute_event_track_wishlisted_ids",
        search="_search_event_track_wishlisted_ids",
        compute_sudo=True,
        groups="event.group_event_user",
    )
    event_track_wishlisted_count = fields.Count(
        count_of="event_track_wishlisted_ids",
        string="# Wishlisted",
        compute_sudo=True,
        groups="event.group_event_user",
    )

    @api.depends(
        "event_track_visitor_ids.track_id", "event_track_visitor_ids.is_wishlisted"
    )
    def _compute_event_track_wishlisted_ids(self):
        results = self.env["event.track.visitor"]._read_group(
            [("visitor_id", "in", self.ids), ("is_wishlisted", "=", True)],
            ["visitor_id"],
            ["track_id:array_agg"],
        )
        track_ids_map = {visitor.id: track_ids for visitor, track_ids in results}
        for visitor in self:
            visitor.event_track_wishlisted_ids = track_ids_map.get(visitor.id, [])

    def _search_event_track_wishlisted_ids(self, operator, operand):
        if operator in ("not in", "not any"):
            raise UserError(
                self.env._("Unsupported 'Not In' operation on track wishlist visitors")
            )

        track_visitors = (
            self.env["event.track.visitor"]
            .sudo()
            .search([("track_id", operator, operand), ("is_wishlisted", "=", True)])
        )

        return [("id", "in", track_visitors.visitor_id.ids)]

    def _get_domain_inactive_visitors(self):
        return super()._get_domain_inactive_visitors() & Domain(
            "event_track_visitor_ids", "=", False
        )

    def _merge_visitor(self, target):
        self.event_track_visitor_ids.visitor_id = target.id
        return super()._merge_visitor(target)
