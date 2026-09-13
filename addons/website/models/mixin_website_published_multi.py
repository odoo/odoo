import logging

from odoo import api, fields
from odoo.fields import Domain
from odoo.libs.web import urljoin as url_join

from .mixin_website_published import MixinWebsitePublished

logger = logging.getLogger(__name__)


class MixinWebsitePublishedMulti(MixinWebsitePublished):
    _name = "mixin.website.published.multi"
    _inherit = ["mixin.website.published", "mixin.website.multi"]
    _description = "Multi Website Published Mixin"

    website_published = fields.Boolean(
        related=False,
        compute="_compute_website_published",
        inverse="_inverse_website_published",
        search="_search_website_published",
        readonly=False,
    )

    @api.depends("is_published", "website_id")
    @api.depends_context("website_id")
    def _compute_website_published(self):
        current_website_id = self.env.context.get("website_id")
        for record in self:
            if current_website_id:
                record.website_published = record.is_published and (
                    not record.website_id or record.website_id.id == current_website_id
                )
            else:
                record.website_published = record.is_published

    def _inverse_website_published(self):
        for record in self:
            record.is_published = record.website_published

    def _search_website_published(self, operator, value):
        if operator != "in" or list(value) != [True]:
            return NotImplemented

        current_website_id = self.env.context.get("website_id")
        is_published = Domain("is_published", "=", True)
        if current_website_id:
            on_current_website = (
                self.env["website"].browse(current_website_id).website_domain()
            )
            return is_published & on_current_website
        else:
            return is_published

    def open_website_url(self):
        website_id = False
        if self.website_id:
            website_id = self.website_id.id
            if self.website_id.domain:
                client_action_url = self.env["website"].get_client_action_url(
                    self.website_url
                )
                client_action_url = f"{client_action_url}&website_id={website_id}"
                return {
                    "type": "ir.actions.act_url",
                    "url": url_join(self.website_id.domain, client_action_url),
                    "target": "self",
                }
        return self.env["website"].get_client_action(
            self.website_url, False, website_id
        )
