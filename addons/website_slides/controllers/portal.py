from odoo.addons.portal.controllers.portal import CustomerPortal


class WebsiteSlidesPortal(CustomerPortal):

    def _prepare_portal_counter_values(self, counter):
        if counter == 'slide_channel_count':
            return 'slide.channel', [('is_visible', '=', True), ('is_member', '=', True)], 'read'
        return super()._prepare_portal_counter_values(counter)
