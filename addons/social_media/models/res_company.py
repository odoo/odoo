from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    social_media_config_id = fields.Many2one(
        comodel_name="social_media.config",
        compute="_compute_social_media_config_id",
        search="_search_social_media_config_id",
    )

    social_twitter = fields.Char(
        related="social_media_config_id.social_twitter",
        readonly=False,
    )
    social_facebook = fields.Char(
        related="social_media_config_id.social_facebook",
        readonly=False,
    )
    social_github = fields.Char(
        related="social_media_config_id.social_github",
        readonly=False,
    )
    social_linkedin = fields.Char(
        related="social_media_config_id.social_linkedin",
        readonly=False,
    )
    social_youtube = fields.Char(
        related="social_media_config_id.social_youtube",
        readonly=False,
    )
    social_instagram = fields.Char(
        related="social_media_config_id.social_instagram",
        readonly=False,
    )
    social_tiktok = fields.Char(
        related="social_media_config_id.social_tiktok",
        readonly=False,
    )
    social_discord = fields.Char(
        related="social_media_config_id.social_discord",
        readonly=False,
    )

    def _search_social_media_config_id(self, operator, value):
        return self._search_config_link("social_media.config", operator, value)

    def _compute_social_media_config_id(self):
        configs = self.env["social_media.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.social_media_config_id = by_company.get(company.id, False)
