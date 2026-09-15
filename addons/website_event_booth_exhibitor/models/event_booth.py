from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class EventBooth(models.Model):
    _inherit = "event.booth"

    use_sponsor = fields.Boolean(related="booth_category_id.use_sponsor")
    sponsor_type_id = fields.Many2one(related="booth_category_id.sponsor_type_id")
    sponsor_id = fields.Many2one(
        comodel_name="event.sponsor",
        copy=False,
    )
    sponsor_name = fields.Char(
        related="sponsor_id.name",
        string="Sponsor Name",
    )
    sponsor_email = fields.Char(
        related="sponsor_id.email",
        string="Sponsor Email",
    )
    sponsor_phone_ids = fields.Many2many(
        related="sponsor_id.phone_ids",
        string="Sponsor Phone",
    )
    sponsor_subtitle = fields.Char(
        related="sponsor_id.subtitle",
        string="Sponsor Slogan",
    )
    sponsor_website_description = fields.Html(
        related="sponsor_id.website_description",
        string="Sponsor Description",
    )
    sponsor_image_512 = fields.Image(
        related="sponsor_id.image_512",
        string="Sponsor Logo",
    )

    def action_view_sponsor(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "website_event_exhibitor.event_sponsor_action"
        )
        action["views"] = [(False, "form")]
        action["res_id"] = self.sponsor_id.id
        return action

    def _get_or_create_sponsor(self, vals):
        self.check_singleton()
        sponsor_id = (
            self.env["event.sponsor"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", self.partner_id.id),
                    ("sponsor_type_id", "=", self.sponsor_type_id.id),
                    ("exhibitor_type", "=", self.booth_category_id.exhibitor_type),
                    ("event_id", "=", self.event_id.id),
                ],
                limit=1,
            )
        )
        _debug.logic(
            "sponsor_lookup",
            booth=self,
            sponsor=sponsor_id,
            partner=self.partner_id,
            event=self.event_id,
        )
        if not sponsor_id:
            values = {
                "event_id": self.event_id.id,
                "sponsor_type_id": self.sponsor_type_id.id,
                "exhibitor_type": self.booth_category_id.exhibitor_type,
                "partner_id": self.partner_id.id,
                **{
                    key.partition("sponsor_")[2]: value
                    for key, value in vals.items()
                    if key.startswith("sponsor_")
                },
            }
            if not values.get("name"):
                values["name"] = self.partner_id.name
            sponsor_id = self.env["event.sponsor"].sudo().create(values)
            _debug.lifecycle(
                "sponsor_created",
                booth=self,
                sponsor=sponsor_id,
                partner=self.partner_id,
                event=self.event_id,
                named_from_partner=not vals.get("sponsor_name"),
            )
        return sponsor_id.id

    def _action_post_confirm(self, write_vals):
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "booths_confirmed",
                booths=self,
                sponsoring=self.filtered(
                    lambda booth: booth.use_sponsor and booth.partner_id
                ),
            )
        for booth in self:
            if booth.use_sponsor and booth.partner_id:
                booth.sponsor_id = booth._get_or_create_sponsor(write_vals)
        super()._action_post_confirm(write_vals)
