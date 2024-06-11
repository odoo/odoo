from odoo.addons.website_event.controllers import main


class WebsiteEventController(main.WebsiteEventController):
    # TODO remove in master
    def _prepare_event_register_values(self, event, **post):
        return super()._prepare_event_register_values(event, **post)
