# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain

from odoo import models


class BusListenerMixin(models.AbstractModel):
    """Allow sending messages related to the current model via as a bus.bus channel.

    The model needs to be allowed as a valid channel for the bus in `_build_bus_channel_list`.
    """

    _name = 'bus.listener.mixin'
    _description = "Can send messages via bus.bus"

    def _bus_send(self, notification_type, message, /, *, subchannel=None):
        """Send a notification to the webclient."""
        for main_channel in self._bus_channels():
            assert isinstance(main_channel, models.Model)
            main_channel.ensure_one()
            channel = main_channel if subchannel is None else (main_channel, subchannel)
            # _sendone: channel is safe (record or tuple with record)
            self.env["bus.bus"]._sendone(channel, notification_type, message)

    def _bus_channels(self):
        return self

    def _bus_join(self, *channels):
        """Make the websockets listening to these records join ``channels`` (records or
        ``(record, subchannel)`` tuples)."""
        self._assert_bus_channels_validity(channels)
        self.env["bus.bus"]._update_subscriptions(self, channels, join=True)

    def _bus_leave(self, *channels):
        """Make the websockets listening to these records leave ``channels`` (records or
        ``(record, subchannel)`` tuples)."""
        self._assert_bus_channels_validity(channels)
        self.env["bus.bus"]._update_subscriptions(self, channels, join=False)

    def _assert_bus_channels_validity(self, channels):
        """Raise unless both sides of the join are the channels ``_bus_send`` delivers
        to: ``_bus_channels()`` resolves to themselves."""
        for channel in chain(self, channels):
            record = channel[0] if isinstance(channel, tuple) else channel
            if record._bus_channels() != record:
                raise ValueError(f"{record} is not a bus channel, use its _bus_channels()")
