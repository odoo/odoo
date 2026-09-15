from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "mixin.website.published.multi"]

    visitor_ids = fields.One2many(
        comodel_name="website.visitor",
        inverse_name="partner_id",
        string="Visitors",
    )

    def google_map_img(self, zoom=8, width=298, height=298):
        google_maps_api_key = (
            self.env["website"].get_current_website().google_maps_api_key
        )
        if not google_maps_api_key:
            _debug.logic("google_map_unavailable", reason="no_api_key")
            return False
        params = {
            "center": "%s, %s %s, %s"
            % (
                self.street or "",
                self.city or "",
                self.zip or "",
                (self.country_id and self.country_id.display_name) or "",
            ),
            "size": "%sx%s" % (width, height),
            "zoom": zoom,
            "sensor": "false",
            "key": google_maps_api_key,
        }
        return "//maps.googleapis.com/maps/api/staticmap?" + urlencode(params)

    def google_map_link(self, zoom=10):
        params = {
            "q": "%s, %s %s, %s"
            % (
                self.street or "",
                self.city or "",
                self.zip or "",
                (self.country_id and self.country_id.display_name) or "",
            ),
            "z": zoom,
        }
        return "https://maps.google.com/maps?" + urlencode(params)

    @api.depends("website_id")
    @api.depends_context("display_website", "uid")
    def _compute_display_name(self):
        super()._compute_display_name()
        if not self.env.context.get("display_website") or not self.env.user.has_group(
            "website.group_multi_website"
        ):
            return
        for partner in self:
            if partner.website_id:
                partner.display_name += f" [{partner.website_id.name}]"
