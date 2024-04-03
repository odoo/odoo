import { mailModels } from "@mail/../tests/mail_test_helpers";
import { Kwargs } from "@web/../tests/_framework/mock_server/mock_server_utils";
import { fields } from "@web/../tests/web_test_helpers";

export class DiscussChannel extends mailModels.DiscussChannel {
    livechat_channel_id = fields.Many2one({ relation: "im_livechat.channel", string: "Channel" }); // FIXME: somehow not fetched properly

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_channel_info"]}
     */
    _channel_info(ids) {
        /** @type {import("mock_models").LivechatChannel} */
        const LivechatChannel = this.env["im_livechat.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const channelInfos = super._channel_info(...arguments);
        for (const channelInfo of channelInfos) {
            const [channel] = this._filter([["id", "=", channelInfo.id]]);
            channelInfo["anonymous_name"] = channel.anonymous_name;
            // add the last message date
            if (channel.channel_type === "livechat") {
                // add the operator id
                if (channel.livechat_operator_id) {
                    const [operator] = ResPartner._filter([
                        ["id", "=", channel.livechat_operator_id],
                    ]);
                    // livechat_username ignored for simplicity
                    channelInfo.operator = ResPartner.mail_partner_format([operator.id])[
                        operator.id
                    ];
                }
                if (channel.livechat_channel_id) {
                    channelInfo.livechatChannel = LivechatChannel.search_read([
                        ["id", "=", channel.livechat_channel_id],
                    ]).map((c) => ({
                        id: c.id,
                        name: c.name,
                    }))[0];
                }
            }
        }
        return channelInfos;
    }
    /** @param {import("mock_models").DiscussChannel} channel */
    _close_livechat_session(channel) {
        if (!channel.livechat_active) {
            return;
        }
        this.write([[channel.id], { livechat_active: false }]);
        if (channel.message_ids.length === 0) {
            return;
        }
        this.message_post(
            channel.id,
            Kwargs({
                body: this._get_visitor_leave_message(),
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            })
        );
    }
    _get_visitor_leave_message() {
        return "Visitor left the conversation.";
    }
    _channel_fetch_message(channelId, lastId, limit) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        const domain = [
            ["model", "=", "discuss.channel"],
            ["res_id", "=", channelId],
        ];
        if (lastId) {
            domain.push(["id", "<", lastId]);
        }
        const messages = MailMessage._message_fetch(domain, limit);
        return MailMessage._message_format(messages.map(({ id }) => id));
    }
    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_types_allowing_seen_infos"]}
     */
    _types_allowing_seen_infos() {
        return super._types_allowing_seen_infos(...arguments).concat(["livechat"]);
    }
}
