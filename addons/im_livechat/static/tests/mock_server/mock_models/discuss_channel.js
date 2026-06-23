import { mailModels } from "@mail/../tests/mail_test_helpers";
import { Store } from "@mail/../tests/mock_server/store";

import { fields, getKwArgs, makeKwArgs, serverState } from "@web/../tests/web_test_helpers";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { ensureArray } from "@web/core/utils/arrays";

const isLivechatChannel = (channel) => channel.channel_type === "livechat";

export class DiscussChannel extends mailModels.DiscussChannel {
    livechat_channel_id = fields.Many2one({ relation: "im_livechat.channel", string: "Channel" }); // FIXME: somehow not fetched properly
    livechat_channel_member_history_ids = fields.One2many({
        relation: "im_livechat.channel.member.history",
    });
    livechat_note = fields.Html({ sanitize: true });
    livechat_status = fields.Selection({
        selection: [("in_progress", "In progress"), ("need_help", "Looking for help")],
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
                    new Store().add(this.browse(channel_id), ["livechat_end_dt"]).as_dict()
                );
            }
        }
        return super.action_unfollow(...arguments);
    }

    /**
     * @override
     * @param {number[]} ids
     * @param {number[]} partner_ids
     * @param {number[]} user_ids
     * @param {boolean} [invite_to_rtc_call=undefined]
     */
    _add_members(ids, partner_ids, user_ids, invite_to_rtc_call) {
        const kwargs = getKwArgs(arguments, "ids", "partner_ids", "user_ids", "invite_to_rtc_call");
        ids = kwargs.ids;
        delete kwargs.ids;
        partner_ids = kwargs.partner_ids || [];
        user_ids = kwargs.user_ids || [];
        const channels = this.browse(
            Array.from(super._add_members(ids, partner_ids, user_ids, invite_to_rtc_call)).map(
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

    _store_channel_fields(res) {
        super._store_channel_fields(res);

        /** @type {import("mock_models").ImLivechatExpertise} */
        const ImLivechatExpertise = this.env["im_livechat.expertise"];
        /** @type {import("mock_models").LivechatChannel} */
        const LivechatChannel = this.env["im_livechat.channel"];
        /** @type {import("mock_models").LivechatChannelMemberHistory} */
        const LivechatChannelMemberHistory = this.env["im_livechat.channel.member.history"];
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];

        res.one("country_id", ["code", "name"], {
            predicate: isLivechatChannel,
            value: (channel) => ResCountry.browse(channel.country_id),
        });
        res.attr("livechat_end_dt", undefined, { predicate: isLivechatChannel });
        // sudo - visitor can access to the channel member history of an accessible channel
        res.many("livechat_channel_member_history_ids", "_store_member_history_fields", {
            predicate: isLivechatChannel,
            sudo: true,
            value: (channel) =>
                LivechatChannelMemberHistory.browse(channel.livechat_channel_member_history_ids),
        });
        if (res.is_for_internal_users()) {
            res.one("livechat_channel_id", ["name"], {
                predicate: isLivechatChannel,
                sudo: true,
                value: (channel) => LivechatChannel.browse(channel.livechat_channel_id),
            });
            res.attr("description", undefined, { predicate: isLivechatChannel });
            res.one("livechat_lang_id", ["name", "code"], {
                predicate: isLivechatChannel,
                value: (channel) => ResLang.browse(channel.livechat_lang_id),
            });
            res.attr(
                "livechat_note",
                (channel) => ["markup", channel.livechat_note], // mock: html fields must be markup-wrapped
                { predicate: isLivechatChannel }
            );
            res.attr("livechat_status", undefined, { predicate: isLivechatChannel });
            res.attr("livechat_looking_for_help_since_dt", undefined, {
                predicate: isLivechatChannel,
            });
            res.many("livechat_expertise_ids", ["name", "color"], {
                predicate: isLivechatChannel,
                value: (channel) => ImLivechatExpertise.browse(channel.livechat_expertise_ids),
            });
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
            new Store().add(this.browse(channel_id), ["livechat_end_dt"]).as_dict()
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
        this._add_members([channel.id], [this.env.user.partner_id]);
        return true;
    }

    /** @type {typeof models.Model["prototype"]["write"]} */
    write(idOrIds, values) {
        const kwargs = getKwArgs(arguments, "ids", "vals");
        ({ ids: idOrIds, vals: values } = kwargs);
        const needHelpBefore = [];
        for (const channel of this._filter([["livechat_status", "=", "need_help"]])) {
            needHelpBefore.push(channel.id);
        }
        if ("livechat_status" in values) {
            values.livechat_looking_for_help_since_dt =
                values.livechat_status === "need_help"
                    ? serializeDateTime(luxon.DateTime.now())
                    : false;
        }
        const result = super.write(idOrIds, values);
        if ("livechat_expertise_ids" in values) {
            // The generic write sync only sends the raw expertise ids; resend them as records so a
            // newly-created expertise reaches the client (mirrors python's bus.sync of the field).
            const ImLivechatExpertise = this.env["im_livechat.expertise"];
            this.env["bus.bus"]._sendmany(
                this.browse(ensureArray(idOrIds)).map((channel) => [
                    channel,
                    "mail.record/insert",
                    new Store()
                        .add(this.browse(channel.id), (res) =>
                            res.many("livechat_expertise_ids", ["name", "color"], {
                                value: ImLivechatExpertise.browse(channel.livechat_expertise_ids),
                            })
                        )
                        .as_dict(),
                ])
            );
        }
        const needHelpAfter = [];
        for (const channel of this._filter([["livechat_status", "=", "need_help"]])) {
            needHelpAfter.push(channel.id);
        }
        const becameNeedHelp = needHelpAfter.filter((id) => !needHelpBefore.includes(id));
        const stoppedNeedHelp = needHelpBefore.filter((id) => !needHelpAfter.includes(id));
        if (becameNeedHelp.length || stoppedNeedHelp.length) {
            this.env["bus.bus"]._sendone(
                [this.env["res.groups"].browse(serverState.groupLivechatId), "LOOKING_FOR_HELP"],
                "mail.record/insert",
                new Store()
                    .add(this.browse(becameNeedHelp), "_store_channel_fields")
                    .add(this.browse(stoppedNeedHelp), ["livechat_status"])
                    .as_dict()
            );
        }

        return result;
    }
}
