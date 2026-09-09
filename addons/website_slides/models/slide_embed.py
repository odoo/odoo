from odoo import _, api, fields, models


class SlideEmbed(models.Model):
    _name = "slide.embed"
    _description = "Embedded Slides View Counter"
    _rec_name = "website_name"

    slide_id = fields.Many2one(
        comodel_name="slide.slide",
        string="Presentation",
        index=True,
        required=True,
        ondelete="cascade",
    )
    url = fields.Char(string="Third Party Website URL")
    website_name = fields.Char(
        string="Website",
        compute="_compute_website_name",
    )
    count_views = fields.Integer(
        string="# Views",
        default=1,
    )

    _slide_id_url_uniq = models.Constraint(
        "unique nulls not distinct (slide_id, url)",
        "A slide can only have one view counter per third-party website URL.",
    )

    @api.depends("url")
    def _compute_website_name(self):
        for slide_embed in self:
            slide_embed.website_name = slide_embed.url or _("Unknown Website")
