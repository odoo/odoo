
from odoo.addons.base.models.assetsbundle import WebAsset

_old_get_stat_attachment_domain = WebAsset._get_stat_attachment_domain

def _new_get_stat_attachment_domain(self):
    domain = _old_get_stat_attachment_domain(self)
    website = self.bundle.env['website'].get_current_website()
    return domain + website.website_domain()

WebAsset._get_stat_attachment_domain = _new_get_stat_attachment_domain
