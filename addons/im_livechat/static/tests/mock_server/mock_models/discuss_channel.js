import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, makeKwArgs } from "@web/../tests/web_test_helpers";

export class DiscussChannel extends mailModels.DiscussChannel {
    livechat_channel_id = fields.Many2one({ relation: "im_livechat.channel", string: "Channel" }); // FIXME: somehow not fetched properly

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_to_store"]}
     */
    _to_store(ids, store) {
        /** @type {import("mock_models").LivechatChannel} */
        const LivechatChannel = this.env["im_livechat.channel"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        super._to_store(...arguments);
        const channels = this._filter([["id", "in", ids]]);
        for (const channel of channels) {
            const channelInfo = { id: channel.id, model: "discuss.channel" };
            channelInfo["anonymous_name"] = channel.anonymous_name;
            // add the last message date
            if (channel.channel_type === "livechat") {
                // add the operator id
                if (channel.livechat_operator_id) {
                    const [operator] = ResPartner._filter([
                        ["id", "=", channel.livechat_operator_id],
                    ]);
                    store.add(ResPartner.browse(operator.id));
                    // livechat_username ignored for simplicity
                    channelInfo.operator = { id: operator.id, type: "partner" };
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
            store.add("Thread", channelInfo);
        }
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
            makeKwArgs({
                body: this._get_visitor_leave_message(),
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
            })
        );
    }
    _get_visitor_leave_message() {
        return "Visitor left the conversation.";
    }

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_types_allowing_seen_infos"]}
     */
    _types_allowing_seen_infos() {
        return super._types_allowing_seen_infos(...arguments).concat(["livechat"]);
    }
}
