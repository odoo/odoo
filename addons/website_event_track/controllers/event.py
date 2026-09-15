from odoo.addons.website_event.controllers.main import WebsiteEventController


class EventOnlineController(WebsiteEventController):
    def _prepare_registration_confirmation_context(self, event, attendees_sudo):
        values = super()._prepare_registration_confirmation_context(event, attendees_sudo)
        values["hide_sponsors"] = True
        return values
