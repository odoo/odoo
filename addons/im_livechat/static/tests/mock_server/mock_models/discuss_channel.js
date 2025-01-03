import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, makeKwArgs } from "@web/../tests/web_test_helpers";
import { ensureArray } from "@web/core/utils/arrays";

export class DiscussChannel extends mailModels.DiscussChannel {
    livechat_channel_id = fields.Many2one({ relation: "im_livechat.channel", string: "Channel" }); // FIXME: somehow not fetched properly

    action_unfollow(idOrIds) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const ids = ensureArray(idOrIds);
        for (const channel_id of ids) {
            const [channel] = this.browse(channel_id);
            if (channel.channel_type == "livechat" && channel.channel_member_ids.length <= 2) {
                this.write([channel.id], { livechat_active: false });
                BusBus._sendone(
                    channel,
                    "mail.record/insert",
                    new mailDataHelpers.Store()
                        .add(this.browse(channel_id), { livechat_active: channel.livechat_active })
                        .get_result()
                );
            }
        }
        return super.action_unfollow(...arguments);
    }
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
                    channelInfo.livechat_operator_id = mailDataHelpers.Store.one(
                        ResPartner.browse(channel.livechat_operator_id),
                        makeKwArgs({ fields: ["user_livechat_username", "write_date"] })
                    );
                } else {
                    channelInfo.livechat_operator_id = false;
                }
                channelInfo["livechat_active"] = channel.livechat_active;
                channelInfo.livechatChannel = mailDataHelpers.Store.one(
                    this.env["im_livechat.channel"].browse(channel.livechat_channel_id),
                    makeKwArgs({ fields: ["name"] })
                );
            }
            store.add(this.browse(channel.id), channelInfo);
        }
    }
    _close_livechat_session(channel_id) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        if (!this.browse(channel_id)[0].livechat_active) {
            return;
        }
        this.write([channel_id], { livechat_active: false });
        const [channel] = this.browse(channel_id);
        BusBus._sendone(
            channel,
            "mail.record/insert",
            new mailDataHelpers.Store()
                .add(this.browse(channel_id), { livechat_active: channel.livechat_active })
                .get_result()
        );
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
