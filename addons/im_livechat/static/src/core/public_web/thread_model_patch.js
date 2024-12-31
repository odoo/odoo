import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.appAsLivechats = Record.one("DiscussApp", {
            compute() {
                return this.channel_type === "livechat" ? this.store.discuss : null;
            },
        });
        this.livechatChannel = Record.one("im_livechat.channel", { inverse: "threads" });
        this.anonymous_country = Record.one("res.country");
    },
    _computeDiscussAppCategory() {
        if (this.channel_type !== "livechat") {
            return super._computeDiscussAppCategory();
        }
        return this.livechatChannel?.appCategory ?? this.appAsLivechats?.defaultLivechatCategory;
    },
    get hasMemberList() {
        return this.channel_type === "livechat" || super.hasMemberList;
    },
    get canLeave() {
        if (this.channel_type === "livechat") {
            return !this.selfMember || this.selfMember.message_unread_counter === 0;
        }
        return super.canLeave;
    },
    get correspondents() {
        return super.correspondents.filter((correspondent) => !correspondent.is_bot);
    },

    computeCorrespondent() {
        let correspondent = super.computeCorrespondent();
        if (this.channel_type === "livechat" && !correspondent) {
            // For livechat threads, the correspondent is the first
            // channel member that is not the operator.
            const orderedChannelMembers = [...this.channel_member_ids].sort((a, b) => a.id - b.id);
            const isFirstMemberOperator = orderedChannelMembers[0]?.persona.eq(this.operator);
            correspondent = isFirstMemberOperator
                ? orderedChannelMembers[1]
                : orderedChannelMembers[0];
        }
        return correspondent;
    },

    get displayName() {
        if (this.channel_type !== "livechat" || !this.correspondent) {
            return super.displayName;
        }
        if (!this.correspondent.persona.is_public && this.correspondent.persona.country) {
            return `${this.correspondent.name} (${this.correspondent.persona.country.name})`;
        }
        if (this.anonymous_country) {
            return `${this.correspondent.name} (${this.anonymous_country.name})`;
        }
        return this.correspondent.name;
    },

    get avatarUrl() {
        if (this.channel_type === "livechat" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }
        return super.avatarUrl;
    },

    /**
     * @override
     * @param {boolean} pushState
     */
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        if (this.store.env.services.ui.isSmall && this.channel_type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
    },
});
