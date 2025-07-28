import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";
import { serializeDate } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";

export class DiscussChannel extends mailModels.DiscussChannel {
    livechat_channel_id = fields.Many2one({ relation: "im_livechat.channel", string: "Channel" }); // FIXME: somehow not fetched properly
    livechat_note = fields.Html({ sanitize: true });
    livechat_status = fields.Selection({
        selection: [
            ("in_progress", "In progress"),
            ("waiting", "Waiting for customer"),
            ("need_help", "Looking for help"),
        ],
    });
    livechat_expertise_ids = fields.Many2many({
        relation: "im_livechat.expertise",
    });

    action_unfollow(idOrIds) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        const ids = ensureArray(idOrIds);
        for (const channel_id of ids) {
            const [channel] = this.browse(channel_id);
            if (channel.channel_type == "livechat" && channel.channel_member_ids.length <= 2) {
                this.write([channel.id], { livechat_end_dt: serializeDate(luxon.DateTime.now()) });
                BusBus._sendone(
                    channel,
                    "mail.record/insert",
                    new mailDataHelpers.Store()
                        .add(this.browse(channel_id), makeKwArgs({ fields: ["livechat_end_dt"] }))
                        .get_result()
                );
            }
        }
        return super.action_unfollow(...arguments);
    }

    /**
     * @override
     * @param {number[]} ids
     * @param {number[]} partner_ids
     * @param {boolean} [invite_to_rtc_call=undefined]
     */
    add_members(ids, partner_ids, invite_to_rtc_call) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids", "invite_to_rtc_call");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];
        const channels = this.browse(
            Array.from(super.add_members(ids, partner_ids, invite_to_rtc_call)).map(
                ({ channel_id }) => channel_id
            )
        );
        for (const channel of channels) {
            if (channel.livechat_status == "need_help") {
                this.write([channel.id], { livechat_status: "in_progress" });
            }
        }
    }

    _channel_basic_info_fields() {
        return [
            ...super._channel_basic_info_fields(),
            "livechat_note",
            "livechat_status",
            "livechat_expertise_ids",
        ];
    }

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_to_store"]}
     */
    _to_store(store) {
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        super._to_store(...arguments);
        for (const channel of this) {
            const channelInfo = {};
            const [country] = ResCountry.browse(channel.country_id);
            channelInfo["country_id"] = country
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
                        makeKwArgs({ fields: ["avatar_128", "user_livechat_username"] })
                    );
                } else {
                    channelInfo.livechat_operator_id = false;
                }
                channelInfo["livechat_end_dt"] = channel.livechat_end_dt;
                channelInfo["livechat_note"] = ["markup", channel.livechat_note];
                channelInfo["livechat_status"] = channel.livechat_status;
                channelInfo["livechat_expertise_ids"] = mailDataHelpers.Store.many(
                    this.env["im_livechat.expertise"].browse(channel.livechat_expertise_ids),
                    makeKwArgs({ fields: ["name"] })
                );
                channelInfo.livechat_channel_id = mailDataHelpers.Store.one(
                    this.env["im_livechat.channel"].browse(channel.livechat_channel_id),
                    makeKwArgs({ fields: ["name"] })
                );
            }
            store._add_record_fields(this.browse(channel.id), channelInfo);
        }
    }
    _close_livechat_session(channel_id) {
        /** @type {import("mock_models").BusBus} */
        const BusBus = this.env["bus.bus"];

        if (this.browse(channel_id)[0].livechat_end_dt) {
            return;
        }
        this.write([channel_id], { livechat_end_dt: serializeDate(luxon.DateTime.now()) });
        const [channel] = this.browse(channel_id);
        BusBus._sendone(
            channel,
            "mail.record/insert",
            new mailDataHelpers.Store()
                .add(this.browse(channel_id), makeKwArgs({ fields: ["livechat_end_dt"] }))
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

    _email_livechat_transcript(channel_id, email) {
        const [channel] = this.browse(channel_id);
        this.message_post(
            channel.id,
            makeKwArgs({
                body: `<div class="o_mail_notification o_hide_author">${this.env.user.name} sent the conversation to ${email}</div>`,
                message_type: "notification",
                subtype_xmlid: "mail.mt_comment",
            })
        );
    }

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_types_allowing_seen_infos"]}
     */
    _types_allowing_seen_infos() {
        return super._types_allowing_seen_infos(...arguments).concat(["livechat"]);
    }

    livechat_join_channel_needing_help(idOrIds) {
        const channel = this.browse(idOrIds)[0];
        if (channel.livechat_status !== "need_help") {
            return false;
        }
        this.add_members([channel.id], [this.env.user.partner_id]);
        return true;
    }
}
