from odoo import _, api, fields, models


class EventEvent(models.Model):
    _inherit = "event.event"

    track_ids = fields.One2many(
        comodel_name="event.track",
        inverse_name="event_id",
        string="Tracks",
    )
    track_count = fields.Integer(compute="_compute_track_count")
    website_track = fields.Boolean(
        string="Tracks on Website",
        compute="_compute_website_track",
        store=True,
        readonly=False,
    )
    website_track_proposal = fields.Boolean(
        string="Proposals on Website",
        compute="_compute_website_track_proposal",
        store=True,
        readonly=False,
    )
    track_menu_ids = fields.One2many(
        comodel_name="website.event.menu",
        inverse_name="event_id",
        string="Event Tracks Menus",
        domain=[("menu_type", "=", "track")],
    )
    track_proposal_menu_ids = fields.One2many(
        comodel_name="website.event.menu",
        inverse_name="event_id",
        string="Event Proposals Menus",
        domain=[("menu_type", "=", "track_proposal")],
    )
    allowed_track_tag_ids = fields.Many2many(
        comodel_name="event.track.tag",
        relation="event_allowed_track_tags_rel",
        string="Available Track Tags",
    )
    tracks_tag_ids = fields.Many2many(
        comodel_name="event.track.tag",
        relation="event_track_tags_rel",
        string="Track Tags",
        compute="_compute_tracks_tag_ids",
        store=True,
    )

    def _compute_track_count(self):
        data = self.env["event.track"]._read_group(
            [("stage_id.is_cancel", "!=", True)], ["event_id"], ["__count"]
        )
        result = {event.id: count for event, count in data}
        for event in self:
            event.track_count = result.get(event.id, 0)

    @api.depends("event_type_id", "website_menu")
    def _compute_website_track(self):
        for event in self:
            if (
                event.event_type_id
                and event.event_type_id != event._origin.event_type_id
            ):
                event.website_track = event.event_type_id.website_track
            elif event.website_menu and (
                event.website_menu != event._origin.website_menu
                or not event.website_track
            ):
                event.website_track = True
            elif not event.website_menu:
                event.website_track = False

    @api.depends("event_type_id", "website_track")
    def _compute_website_track_proposal(self):
        for event in self:
            if (
                event.event_type_id
                and event.event_type_id != event._origin.event_type_id
            ):
                event.website_track_proposal = (
                    event.event_type_id.website_track_proposal
                )
            elif (
                event.website_track != event._origin.website_track
                or not event.website_track
                or not event.website_track_proposal
            ):
                event.website_track_proposal = event.website_track

    @api.depends("track_ids.tag_ids", "track_ids.tag_ids.color")
    def _compute_tracks_tag_ids(self):
        for event in self:
            event.tracks_tag_ids = (
                event.track_ids.mapped("tag_ids")
                .filtered(lambda tag: tag.color != 0)
                .ids
            )

    def _has_published_track(self):
        self.check_singleton()
        return bool(self.track_ids.filtered("is_published"))

    def toggle_website_track(self, val):
        self.website_track = val

    def toggle_website_track_proposal(self, val):
        self.website_track_proposal = val

    def copy_event_menus(self, old_events):
        super().copy_event_menus(old_events)
        for new_event in self:
            (
                new_event.track_menu_ids + new_event.track_proposal_menu_ids
            ).menu_id.parent_id = new_event.menu_id

    def _get_fields_menu_update(self):
        return super()._get_fields_menu_update() + [
            "website_track",
            "website_track_proposal",
        ]

    def _update_website_menus(self, menus_update_by_field=None):
        super()._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (
                not menus_update_by_field
                or event in menus_update_by_field.get("website_track")
            ):
                event._update_website_menu_entry(
                    "website_track", "track_menu_ids", "track"
                )
            if event.menu_id and (
                not menus_update_by_field
                or event in menus_update_by_field.get("website_track_proposal")
            ):
                event._update_website_menu_entry(
                    "website_track_proposal",
                    "track_proposal_menu_ids",
                    "track_proposal",
                )

    def _get_menu_type_field_matching(self):
        res = super()._get_menu_type_field_matching()
        res["track_proposal"] = "website_track_proposal"
        return res

    def _get_website_menu_entries(self):
        self.check_singleton()
        return super()._get_website_menu_entries() + [
            (_("Talks"), "#", False, 10, "track", False),
            (
                _("Talks"),
                "/event/%s/track" % self.env["ir.http"]._slug(self),
                False,
                10,
                "track",
                "track",
            ),
            (
                _("Agenda"),
                "/event/%s/agenda" % self.env["ir.http"]._slug(self),
                False,
                15,
                "track",
                "track",
            ),
            (
                _("Propose a talk"),
                "/event/%s/track_proposal" % self.env["ir.http"]._slug(self),
                False,
                20,
                "track_proposal",
                "track",
            ),
        ]
