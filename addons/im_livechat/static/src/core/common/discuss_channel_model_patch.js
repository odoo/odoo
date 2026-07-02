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
        this.chatbot_current_step_id = fields.One("chatbot.script.step", {
            onUpdate() {
                if (this.chatbot && !this.chatbot_current_step_id) {
                    this.chatbotTriggerFailedError = null;
                    this.chatbot.stop();
                }
            },
        });
        this.country_id = fields.One("res.country");
        this.livechat_agent_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsAgentHistory",
        });
        this.livechat_bot_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsBotHistory",
        });
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "channel_ids" });
        this.livechat_channel_member_history_ids = fields.Many(
            "im_livechat.channel.member.history",
            { inverse: "channel_id" }
        );
        this.livechat_customer_history_ids = fields.Many("im_livechat.channel.member.history", {
            inverse: "channelAsCustomerHistory",
        });
        this.livechat_customer_partner_ids = fields.Many("res.partner");
        this.livechat_expertise_ids = fields.Many("im_livechat.expertise");
        this.livechat_lang_id = fields.One("res.lang");
        this.livechat_looking_for_help_since_dt = fields.Datetime();
        /** @type {"in_progress"|"need_help"|undefined} */
        this.livechat_status = undefined;
        this.livechat_end_dt = fields.Datetime();
        this.livechat_operator_id = fields.One("res.partner");
        /** @type {string|undefined} */
        this.livechat_outcome = undefined;
        this.livechat_note = fields.Html();
        /** @type {string|undefined} */
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
        /** @type {import("@web/core/network/rpc").RPCError|import("@web/core/network/rpc").ConnectionLostError|import("@web/core/network/rpc").ConnectionAbortedError|undefined} */
        this.chatbotTriggerFailedError = undefined;
        this._toggleChatbot = fields.Attr(false, {
            compute() {
                return Boolean(this.chatbot && !this.chatbot.completed && !this.livechat_end_dt);
            },
            onUpdate() {
                const shouldToggle = this._toggleChatbot;
                this.isLoadedPromise.then(() => {
                    if (shouldToggle) {
                        this.chatbot.start();
                    } else {
                        this.chatbot?.stop();
                    }
                });
            },
            eager: true,
        });
    },
    get allowDescriptionTypes() {
        return [...super.allowDescriptionTypes, "livechat"];
    },
    get allowEditDescription() {
        if (this.self_member_id?.livechat_member_type === "visitor") {
            return false;
        }
        return (
            super.allowEditDescription ||
            (this.channel_type === "livechat" && this.store.has_access_livechat)
        );
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    get avatarUrl() {
        if (
            this.channel_type === "livechat" &&
            (this.isTransient || this.self_member_id?.livechat_member_type === "visitor")
        ) {
            let bestScore = -1;
            let bestMemberHistory;
            // Agents are preferred over bots, current members over former members, and higher IDs over lower IDs
            for (const memberHistory of this.livechat_channel_member_history_ids.sort(
                (a, b) => b.id - a.id
            )) {
                if (memberHistory.livechat_member_type === "visitor") {
                    continue;
                }
                const score =
                    (memberHistory.livechat_member_type === "agent" ? 4 : 0) +
                    (memberHistory.member_id ? 2 : 0);
                if (score > bestScore) {
                    bestScore = score;
                    bestMemberHistory = memberHistory;
                }
            }
            return bestMemberHistory?.partner_id?.avatarUrl || super.avatarUrl;
        }
        return super.avatarUrl;
    },
    /** @override */
    _computeCanHide() {
        if (this.channel_type === "livechat") {
            return (
                this.isLocallyPinned && !this.self_member_id && this.livechat_status !== "need_help"
            );
        }
        return super._computeCanHide(...arguments);
    },
    get computedDisplayName() {
        if (this.channel_type !== "livechat") {
            return super.computedDisplayName;
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
            let histories = this.livechat_customer_history_ids;
            if (selfMemberType === "visitor") {
                histories = this.livechat_agent_history_ids.length
                    ? this.livechat_agent_history_ids
                    : this.livechat_bot_history_ids;
            }
            memberNames = histories
                .map((h) => this.getPersonaName(h.partner_id || h.guest_id))
                .filter(Boolean);
        }
        return memberNames.length
            ? formatList(memberNames, { style: "standard-narrow" })
            : super.computedDisplayName;
    },
    get isHideUntilNewMessageSupported() {
        if (this.livechat_end_dt) {
            return false;
        }
        return super.isHideUntilNewMessageSupported;
    },
    get isLastMessageFromCustomer() {
        return this.newestPersistentOfAllMessage?.author?.eq(this.livechatVisitorMember?.persona);
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
        const hasOtherAgent = this.channel_member_ids.some(
            (m) => m.livechat_member_type === "agent" && m.notEq(this.self_member_id)
        );
        return this.self_member_id.livechat_member_type === "visitor" || !hasOtherAgent;
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
        if (this.channel_type !== "livechat") {
            return super.composerHidden;
        }
        if (this.self_member_id?.livechat_member_type === "visitor") {
            return (
                super.composerHidden ||
                this.livechat_end_dt ||
                (this.chatbot?.completed && !this.livechat_agent_history_ids.length)
            );
        }
        return !!this.livechat_end_dt;
    },

    get composerHiddenText() {
        if (this.channel?.channel_type === "livechat" && this.livechat_end_dt) {
            return _t("This live chat conversation has ended.");
        }
        return super.composerHiddenText;
    },
    get transcriptUrl() {
        return url(`/im_livechat/download_transcript/${this.id}`);
    },
    shouldNotifyMessageToUser() {
        if (this.self_member_id?.livechat_member_type === "visitor") {
            return true;
        }
        return super.shouldNotifyMessageToUser(...arguments);
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
