from odoo import models


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    def _get_current_pages_and_models_dict(self):
        return super()._get_current_pages_and_models_dict() | {
            "blog": "blog.blog",
        }
