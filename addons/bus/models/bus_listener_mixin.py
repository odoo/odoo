# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class BusListenerMixin(models.AbstractModel):
    """Allow sending messages related to the current model via as a bus.bus channel.

    The model needs to be allowed as a valid channel for the bus in `_build_bus_channel_list`.
    """

    _name = 'bus.listener.mixin'
    _description = "Can send messages via bus.bus"

    def _bus_send(self, notification_type, message, /, *, subchannel=None):
        """Send a notification to the webclient."""
        for record in self:
            main_channel = record
            while (new_main_channel := main_channel._bus_channel()) != main_channel:
                main_channel = new_main_channel
            assert isinstance(main_channel, models.Model)
            if not main_channel:
                continue
            main_channel.ensure_one()
            channel = main_channel if subchannel is None else (main_channel, subchannel)
            # _sendone: channel is safe (record or tuple with record)
            self.env["bus.bus"]._sendone(channel, notification_type, message)

    def _bus_channel(self):
        return self
