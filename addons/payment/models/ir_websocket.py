# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.payment import utils as payment_utils


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        """
        When `_send_bus` is called, it sends notifications to channels based on the record type and
        record id.

        In the frontend, `payment.transaction` records cannot be directly used as channels, so a
        string channel containing the transaction id and an access token is used instead.

        This method detects such channels, matching the pattern
        "payment_transaction_channel:<id>,<token>", validates the access token, and replaces them
        with the corresponding `payment.transaction` record.

        Channels that do not match or fail validation are filtered out.
        """
        new_channels = []
        for channel in channels:
            if isinstance(channel, str) and "payment_transaction_channel" in channel:
                data = channel.split(":")[1]
                tx_id, access_token = data.split(",")
                if tx_id.isdigit() and (
                    tx := self.env["payment.transaction"].browse(int(tx_id)).exists()
                ):
                    if payment_utils.generate_access_token([tx.id], env=self.env) == access_token:
                        new_channels.append(tx)
            else:
                new_channels.append(channel)
        return super()._build_bus_channel_list(new_channels)
