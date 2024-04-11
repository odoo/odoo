# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers import mail


class PortalChatter(mail.PortalChatter):

    def _portal_post_filter_params(self):
        fields = super(PortalChatter, self)._portal_post_filter_params()
        fields += ['rating_value']
        return fields
