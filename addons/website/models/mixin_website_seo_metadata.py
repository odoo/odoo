import logging
import urllib.parse

from odoo import api, fields, models
from odoo.http import request
from odoo.libs.web import urljoin as url_join

logger = logging.getLogger(__name__)


class MixinWebsiteSeoMetadata(models.AbstractModel):
    _name = "mixin.website.seo.metadata"

    _description = "SEO metadata"

    is_seo_optimized = fields.Boolean(
        string="SEO optimized",
        compute="_compute_is_seo_optimized",
        precompute=True,
        store=True,
    )
    website_meta_title = fields.Char(
        string="Website meta title",
        translate=True,
        prefetch="website_meta",
    )
    website_meta_description = fields.Text(
        string="Website meta description",
        translate=True,
        prefetch="website_meta",
    )
    website_meta_keywords = fields.Char(
        string="Website meta keywords",
        translate=True,
        prefetch="website_meta",
    )
    website_meta_og_img = fields.Char(string="Website opengraph image")
    seo_name = fields.Char(
        string="Seo name",
        translate=True,
        prefetch=True,
    )

    @api.depends(
        "website_meta_title", "website_meta_description", "website_meta_keywords"
    )
    def _compute_is_seo_optimized(self):
        for record in self:
            record.is_seo_optimized = bool(
                record.website_meta_title
                and record.website_meta_description
                and record.website_meta_keywords
            )

    def _get_default_website_meta(self):
        self.check_singleton()
        company = request.website.company_id.sudo()
        title = request.website.name
        if "name" in self:
            title = "%s | %s" % (self.name, title)

        img_field = (
            "social_default_image"
            if request.website.has_social_default_image
            else "logo"
        )

        default_opengraph = {
            "og:type": "website",
            "og:title": title,
            "og:site_name": request.website.name,
            "og:url": url_join(
                request.website.domain or request.httprequest.url_root,
                self.env["ir.http"]._url_for(request.httprequest.path),
            ),
            "og:image": request.website.image_url(request.website, img_field),
        }
        default_twitter = {
            "twitter:card": "summary_large_image",
            "twitter:title": title,
            "twitter:image": request.website.image_url(
                request.website, img_field, size="300x300"
            ),
        }
        if company.social_twitter:
            default_twitter["twitter:site"] = (
                "@%s" % company.social_twitter.split("/")[-1]
            )

        return {
            "default_opengraph": default_opengraph,
            "default_twitter": default_twitter,
        }

    def get_website_meta(self):
        root_url = request.website.domain or request.httprequest.url_root.strip("/")
        default_meta = self._get_default_website_meta()
        opengraph_meta, twitter_meta = (
            default_meta["default_opengraph"],
            default_meta["default_twitter"],
        )
        if self.website_meta_title:
            opengraph_meta["og:title"] = self.website_meta_title
            twitter_meta["twitter:title"] = self.website_meta_title
        if self.website_meta_description:
            opengraph_meta["og:description"] = self.website_meta_description
            twitter_meta["twitter:description"] = self.website_meta_description
        og_image = self.website_meta_og_img and urllib.parse.urlunsplit(
            ["", "", *urllib.parse.urlsplit(self.website_meta_og_img)[2:]]
        )
        opengraph_meta["og:image"] = url_join(
            root_url,
            self.env["ir.http"]._url_for(og_image or opengraph_meta["og:image"]),
        )
        twitter_meta["twitter:image"] = url_join(
            root_url,
            self.env["ir.http"]._url_for(og_image or twitter_meta["twitter:image"]),
        )
        return {
            "opengraph_meta": opengraph_meta,
            "twitter_meta": twitter_meta,
            "meta_description": default_meta.get("default_meta_description"),
        }
