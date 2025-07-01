import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, makeKwArgs } from "@web/../tests/web_test_helpers";

export class DiscussChannel extends mailModels.DiscussChannel {
    livechat_channel_id = fields.Many2one({ relation: "im_livechat.channel", string: "Channel" }); // FIXME: somehow not fetched properly

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_to_store"]}
     */
    _to_store(ids, store) {
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        super._to_store(...arguments);
        const channels = this.browse(ids);
        for (const channel of channels) {
            const channelInfo = {};
            channelInfo["anonymous_name"] = channel.anonymous_name;
            const [country] = ResCountry.browse(channel.country_id);
            channelInfo["anonymous_country"] = country
                ? {
                      code: country.code,
                      id: country.id,
                      name: country.name,
                  }
                : false;
            // add the last message date
            if (channel.channel_type === "livechat") {
                // add the operator id
                if (channel.livechat_operator_id) {
                    // livechat_username ignored for simplicity
                    channelInfo.operator = mailDataHelpers.Store.one(
                        ResPartner.browse(channel.livechat_operator_id),
                        makeKwArgs({ fields: ["avatar_128", "user_livechat_username"] })
                    );
                } else {
                    channelInfo.operator = false;
                }
                channelInfo.livechatChannel = mailDataHelpers.Store.one(
                    this.env["im_livechat.channel"].browse(channel.livechat_channel_id),
                    makeKwArgs({ fields: ["name"] })
                );
            }
            store.add(this.browse(channel.id), channelInfo);
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
