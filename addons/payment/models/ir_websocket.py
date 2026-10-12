# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.payment import utils as payment_utils


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _subscribe(self, og_data):
        """Override of `bus` to send the current status of the subscribed transactions.

        The transactions might have been post-processed and their status notified to the client
        before the subscription to the channel was established. Since the bus only replays
        notifications that are newer than the last one received by the client's worker, we resend
        the status. Only post-processed transactions are resent to prevent redirecting the client
        before post-processing is complete.

        :param dict og_data: The subscription data sent by the client
        :rtype: None
        """
        super()._subscribe(og_data)  # Calls `_build_bus_channel_list`
        for channel in og_data["channels"]:
            if isinstance(channel, str) and "payment_transaction_channel" in channel:
                tx = self._get_transaction_from_channel(channel)
                # At this point, the access token has been verified
                tx_sudo = tx.sudo()  # Sudo to read the status values
                if tx_sudo.is_post_processed:
                    tx_sudo._notify_status()

    def _build_bus_channel_list(self, channels):
        """Override of `bus` to register `payment.transaction` records as channels.

        When `_send_bus` is called, it sends notifications to channels based on the record type
        and record id.

        In the frontend, `payment.transaction` records cannot be directly used as channels, so a
        string channel containing the transaction id and an access token is used instead.

        This method detects such channels, matching the pattern
        "payment_transaction_channel:<id>,<token>", validates the access token, and replaces them
        with the corresponding `payment.transaction` record.

        Channels that do not match or fail validation are filtered out.

        :param list[any] channels: The channel list sent by the client.
        :return: The filtered channel list.
        :rtype: list[any]
        """
        new_channels = []
        for channel in channels:
            if isinstance(channel, str) and "payment_transaction_channel" in channel:
                if tx := self._get_transaction_from_channel(channel):
                    new_channels.append(tx)
            else:
                new_channels.append(channel)
        return super()._build_bus_channel_list(new_channels)

    def _get_transaction_from_channel(self, channel):
        """Return the transaction encoded in the channel if the access token is valid.

        :param str channel: The channel string, formatted as
                            "payment_transaction_channel:<id>,<token>"
        :return: The encoded transaction if the channel is valid
        :rtype: payment.transaction
        """
        channel_values = channel.split(":")[1]
        tx_id, access_token = channel_values.split(",")
        if (
            tx_id.isdigit()
            and (tx := self.env["payment.transaction"].browse(int(tx_id)).exists())
            and payment_utils.generate_access_token(tx.id, env=self.env) == access_token
        ):
            return tx
        return self.env["payment.transaction"]
