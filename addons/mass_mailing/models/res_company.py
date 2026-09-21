from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_social_media_links(self):
        self.check_singleton()
        return {
            "social_facebook": self.social_media_config_id.social_facebook,
            "social_linkedin": self.social_media_config_id.social_linkedin,
            "social_twitter": self.social_media_config_id.social_twitter,
            "social_instagram": self.social_media_config_id.social_instagram,
            "social_tiktok": self.social_media_config_id.social_tiktok,
        }
