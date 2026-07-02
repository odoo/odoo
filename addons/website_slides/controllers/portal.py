from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class WebsiteSlidesPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'slide_channel_count' in counters:
            # Count follows the number of channels displayed in the "My courses" section on /slides
            values['slide_channel_count'] = request.env['slide.channel'].search_count(
                [] if self.env.user._is_public() else [('is_visible', '=', True), ('is_member', '=', True)]
            )

        return values
