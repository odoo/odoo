import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.libs.web import urljoin as url_join

logger = logging.getLogger(__name__)


class MixinWebsitePublished(models.AbstractModel):
    _name = "mixin.website.published"

    _description = "Website Published Mixin"

    website_published = fields.Boolean(
        related="is_published",
        string="Visible on current website",
        readonly=False,
    )
    is_published = fields.Boolean(
        default=lambda self: self._default_is_published(),
        index=True,
        copy=False,
    )
    can_publish = fields.Boolean(compute="_compute_can_publish")
    website_url = fields.Char(
        string="Website URL",
        compute="_compute_website_url",
        help="The full relative URL to access the document through the website.",
    )
    website_absolute_url = fields.Char(
        string="Website Absolute URL",
        compute="_compute_website_absolute_url",
        help="The full absolute URL to access the document through the website.",
    )

    @api.depends_context("lang")
    def _compute_website_url(self):
        for record in self:
            record.website_url = "#"

    @api.depends("website_url")
    def _compute_website_absolute_url(self):
        self.website_absolute_url = "#"
        for record in self:
            if record.website_url != "#":
                record.website_absolute_url = url_join(
                    record.get_base_url(), record.website_url
                )

    def _default_is_published(self):
        return False

    def website_publish_button(self):
        self.check_singleton()
        value = not self.website_published
        self.write({"website_published": value})
        return value

    def open_website_url(self):
        return self.env["website"].get_client_action(self.website_url)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(record.is_published and not record.can_publish for record in records):
            raise AccessError(self._get_can_publish_error_message())

        return records

    def write(self, vals):
        if "is_published" in vals and any(not record.can_publish for record in self):
            raise AccessError(self._get_can_publish_error_message())

        return super().write(vals)

    def create_and_get_website_url(self, **kwargs):
        return self.create(kwargs).website_url

    @api.depends_context("uid")
    def _compute_can_publish(self):
        modifiable = self.env["website"].get_current_website()._filter_modifiable(self)
        for record in self:
            record.can_publish = record in modifiable

    @api.model
    def _get_can_publish_error_message(self):
        return _("You do not have the rights to publish/unpublish")
