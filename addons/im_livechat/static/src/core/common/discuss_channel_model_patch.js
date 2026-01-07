import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { fields } from "@mail/model/misc";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { formatList } from "@web/core/l10n/utils";
import { url } from "@web/core/utils/urls";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.chatbot = fields.One("Chatbot", { inverse: "channel_id" });
        this.country_id = fields.One("res.country");
        this.livechat_agent_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsAgentHistory",
        });
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "channel_ids" });
        this.livechat_channel_member_history_ids = fields.Many(
            "im_livechat.channel.member.history",
            { inverse: "channel_id" }
        );
        this.livechat_customer_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsCustomerHistory",
        });
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        this.livechat_lang_id = fields.One("res.lang");
        this.livechat_looking_for_help_since_dt = fields.Datetime();
        /** @type {"in_progress"|"need_help"|undefined} */
        this.livechat_status = fields.Attr(undefined, {
            onUpdate() {
                if (this.livechat_status === "need_help") {
                    this.wasLookingForHelp = true;
                    this.unpinOnThreadSwitch = false;
                    return;
                }
                if (this.wasLookingForHelp) {
                    this.wasLookingForHelp = false;
                    // Still the active thread; keep it pinned after leaving "need help" status.
                    // The agent may interact with the thread, keeping it pinned, or it will be
                    // unpinned on the next thread switch to avoid bloating the sidebar.
                    this.unpinOnThreadSwitch = this.eq(this.store.discuss?.thread?.channel);
                }
            },
        });
        this.unpinOnThreadSwitch = false;
        this.livechat_end_dt = fields.Datetime();
        this.livechat_operator_id = fields.One("res.partner");
        /** @type {string|undefined} */
        this.livechat_note = fields.Html();
        this.livechatNoteText = fields.Attr(undefined, {
            compute() {
                if (this.livechat_note !== undefined) {
                    return convertBrToLineBreak(this.livechat_note || "");
                }
                return this.livechatNoteText;
            },
        });
        this.livechatVisitorMember = fields.One("discuss.channel.member", {
            compute() {
                if (this.channel_type !== "livechat") {
                    return;
                }
                return [...this.channel_member_ids]
                    .sort((a, b) => a.id - b.id)
                    .find((member) => member.livechat_member_type === "visitor");
            },
        });
    },
    get allowDescriptionTypes() {
        return [...super.allowDescriptionTypes, "livechat"];
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    /** @override */
    _computeCanHide() {
        if (this.channel_type === "livechat") {
            return false;
        }
        return super._computeCanHide(...arguments);
    },
    get displayName() {
        if (this.channel_type !== "livechat") {
            return super.displayName;
        }
        const selfMemberType = this.isTransient
            ? "visitor"
            : this.self_member_id?.livechat_member_type;
        let memberNames = this.correspondents
            .filter((m) => {
                if (selfMemberType === "visitor") {
                    return m.livechat_member_type === "agent";
                }
                return m.livechat_member_type === "visitor";
            })
            .map((m) => m.name);
        if (!memberNames.length) {
            const histories =
                selfMemberType === "visitor"
                    ? this.livechat_agent_history_ids
                    : this.livechat_customer_history_ids;
            memberNames = histories
                .map((h) => this.getPersonaName(h.partner_id || h.guest_id))
                .filter(Boolean);
        }
        return memberNames.length
            ? formatList(memberNames, { style: "standard-narrow" })
            : super.displayName;
    },
    get isHideUntilNewMessageSupported() {
        if (this.livechat_end_dt) {
            return false;
        }
        return super.isHideUntilNewMessageSupported;
    },
    get livechatShouldAskLeaveConfirmation() {
        if (
            this.isTransient ||
            this.livechat_end_dt ||
            !this.self_member_id ||
            this.channel_type !== "livechat"
        ) {
            return false;
        }
        return (
            this.self_member_id.livechat_member_type === "visitor" ||
            this.channel_member_ids.length <= 2
        );
    },
    get typesAllowingCalls() {
        return [...super.typesAllowingCalls, "livechat"];
    },
    get membersThatCanSeen() {
        return super.membersThatCanSeen.filter((member) => member.livechat_member_type !== "bot");
    },
    get chatChannelTypes() {
        return [...super.chatChannelTypes, "livechat"];
    },
    get memberListTypes() {
        return [...super.memberListTypes, "livechat"];
    },
    get showCorrespondentCountry() {
        if (this.channel_type === "livechat") {
            return (
                this.correspondent?.livechat_member_type === "visitor" &&
                Boolean(this.correspondentCountry)
            );
        }
        return super.showCorrespondentCountry;
    },
    get showImStatus() {
        if (this.self_member_id?.livechat_member_type === "visitor") {
            return false;
        }
        return (this.channel_type === "livechat" && this.correspondent) || super.showImStatus;
    },
    get allow_invite_by_email() {
        return this.channel_type === "livechat" || super.allow_invite_by_email;
    },
    get composerHidden() {
        if (this.channel?.channel_type === "livechat") {
            return !!this.livechat_end_dt;
        }
        return super.composerHidden;
    },

    get composerHiddenText() {
        if (this.channel?.channel_type === "livechat" && this.livechat_end_dt) {
            return _t("This live chat conversation has ended");
        }
        return super.composerHiddenText;
    },
    get transcriptUrl() {
        return url(`/im_livechat/download_transcript/${this.id}`);
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
