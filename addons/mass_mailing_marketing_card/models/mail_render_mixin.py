from odoo import models


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    def _shorten_links_get_default_blacklist(self, blacklist):
        """Override to always blacklist marketing cards URLs as they are always dynamic."""
        blacklist = super()._shorten_links_get_default_blacklist(blacklist)
        return (blacklist or []) + ['/cards/']
