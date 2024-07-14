/* @odoo-module */

import "@mail/../tests/helpers/mock_server/models/discuss_channel"; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.model === "discuss.channel" && args.method === "whatsapp_channel_join_and_pin") {
            const ids = args.args[0];
            return this._mockDiscussChannelJoinAndPin(ids);
        }
        return super._performRPC(route, args);
    },
    /**
     * @override
     */
    _mockDiscussChannelChannelInfo(ids) {
        const channelInfos = super._mockDiscussChannelChannelInfo(...arguments);
        for (const channelInfo of channelInfos) {
            const channel = this.getRecords("discuss.channel", [["id", "=", channelInfo.id]])[0];
            channelInfo["anonymous_name"] = channel.anonymous_name;
            if (
                channel.channel_type === "whatsapp" &&
                Boolean(channel.whatsapp_channel_valid_until)
            ) {
                channelInfo["whatsapp_channel_valid_until"] = channel.whatsapp_channel_valid_until;
            }
        }
        return channelInfos;
    },
    _mockDiscussChannelJoinAndPin(ids) {
        const [channel] = this.getRecords("discuss.channel", [["id", "in", ids]]);
        const [currentPartnerMember] = this.getRecords("discuss.channel.member", [
            ["channel_id", "=", channel.id],
            ["partner_id", "=", this.pyEnv.currentPartnerId],
        ]);
        if (currentPartnerMember) {
            this.pyEnv["discuss.channel.member"].write([currentPartnerMember.id], {
                is_pinned: true,
            });
        } else {
            this.pyEnv["discuss.channel.member"].create({
                channel_id: channel.id,
                partner_id: this.pyEnv.currentPartnerId,
            });
            const body = "<div class='o_mail_notification'>joined the channel</div>";
            const message_type = "notification";
            const subtype_xmlid = "mail.mt_comment";
            this._mockDiscussChannelMessagePost(channel.id, { body, message_type, subtype_xmlid });
        }
        return this._mockDiscussChannelChannelInfo([channel.id])[0];
    },
});
