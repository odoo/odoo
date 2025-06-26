/** @odoo-module alias=@mail/../tests/helpers/mock_server/controllers/discuss/channel default=false */

import "@mail/../tests/helpers/mock_server/controllers/webclient"; // ensure super is loaded first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /** @override */
    _mockRoute_ProcessRequest(args) {
        const res = super._mockRoute_ProcessRequest(args);
        if (args.channels_as_member) {
            const channels = this._mockDiscussChannel__get_channels_as_member();
            this._addToRes(res, {
                "mail.message": channels
                    .map((channel) => {
                        const channelMessages = this.getRecords("mail.message", [
                            ["model", "=", "discuss.channel"],
                            ["res_id", "=", channel.id],
                        ]);
                        const lastMessage = channelMessages.reduce((lastMessage, message) => {
                            if (message.id > lastMessage.id) {
                                return message;
                            }
                            return lastMessage;
                        }, channelMessages[0]);
                        return lastMessage
                            ? this._mockMailMessageMessageFormat([lastMessage.id])[0]
                            : false;
                    })
                    .filter((lastMessage) => lastMessage),
                "discuss.channel": this._mockDiscussChannelChannelInfo(
                    channels.map((channel) => channel.id)
                ),
            });
        }
        return res;
    },
});
