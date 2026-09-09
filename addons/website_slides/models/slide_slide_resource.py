from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.filesystem import get_extension


class SlideSlideResource(models.Model):
    _name = "slide.slide.resource"
    _description = "Additional resource for a particular slide"
    _order = "sequence, id"

    slide_id = fields.Many2one(
        comodel_name="slide.slide",
        index=True,
        required=True,
        ondelete="cascade",
    )
    resource_type = fields.Selection(
        selection=[("file", "File"), ("url", "Link")],
        required=True,
    )
    name = fields.Char(
        compute="_compute_name",
        inverse="_inverse_name",
        store=True,
        readonly=False,
    )
    is_name_default = fields.Boolean(default=True, copy=False)
    data = fields.Binary(
        string="Resource",
        compute="_compute_reset_resources",
        store=True,
        readonly=False,
    )
    file_name = fields.Char(store=True)
    link = fields.Char(
        compute="_compute_reset_resources",
        store=True,
        readonly=False,
    )
    download_url = fields.Char(
        string="Download URL",
        compute="_compute_download_url",
    )
    sequence = fields.Integer()

    _check_url = models.Constraint(
        "CHECK (resource_type != 'url' OR link IS NOT NULL)",
        "A resource of type url must contain a link.",
    )
    _check_file_type = models.Constraint(
        "CHECK (resource_type != 'file' OR link IS NULL)",
        "A resource of type file cannot contain a link.",
    )

    @api.depends("resource_type")
    def _compute_reset_resources(self):
        for resource in self:
            if resource.resource_type == "file":
                resource.link = False
                resource.data = resource.data
            else:
                resource.data = False
                resource.link = resource.link

    @api.depends("file_name", "resource_type", "data", "link")
    def _compute_name(self):
        # `is_name_default` (language-independent) replaces comparing `name`
        # against a live-translated `_("Resource")`, which broke as soon as a
        # resource created under one user language was later written to
        # under another: the stored placeholder never matched the newly
        # translated comparison string, so it was never replaced.
        for resource in self:
            if not resource.name or resource.is_name_default:
                new_name = _("Resource")
                if resource.resource_type == "file" and (
                    resource.data or resource.file_name
                ):
                    new_name = resource.file_name
                elif resource.resource_type == "url":
                    new_name = resource.link
                resource.name = new_name
            else:
                resource.name = resource.name

    def _inverse_name(self):
        self.is_name_default = False

    @api.depends("name", "file_name")
    def _compute_download_url(self):
        for resource in self:
            extension = get_extension(resource.file_name) if resource.file_name else ""
            if not resource.name:
                resource.download_url = False
                continue
            file_name = (
                resource.name
                if resource.name.endswith(extension)
                else resource.name + extension
            )
            resource.download_url = (
                f"/web/content/slide.slide.resource/{resource.id}/data?"
                + urlencode(
                    {
                        "download": "true",
                        "filename": file_name,
                    }
                )
            )

    @api.constrains("data")
    def _check_link_type(self):
        for record in self:
            if record.resource_type != "file" and record.data:
                raise ValidationError(
                    _(
                        "Resource %(resource_name)s is a link and should not contain a data file",
                        resource_name=record.name,
                    )
                )
