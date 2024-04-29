from odoo import models, api


class BusListenerMixin(models.AbstractModel):
    """Allow sending messages related to the current model via as a bus.bus channel.

    The model needs to be allowed as a valid channel for the bus in `_build_bus_channel_list`.
    """
    _name = 'bus.listener.mixin'
    _description = "Can send messages via bus.bus"

    @api.model
    def _bus_send(self, notification_type, message, subchannel=None):
        """Send a notification to the webclient."""
        for record in self:
            main_channel = record._bus_channel()
            assert isinstance(main_channel, models.Model)
            channel = main_channel if subchannel is None else (main_channel, subchannel)
            self.env['bus.bus']._add_to_queue(channel, notification_type, message)

    def _bus_channel(self):
        return self
