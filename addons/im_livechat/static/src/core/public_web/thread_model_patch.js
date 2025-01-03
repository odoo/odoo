import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

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
        const correspondent = super.computeCorrespondent();
        if (this.channel_type === "livechat" && !correspondent) {
            return this.livechatVisitorMember;
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
    async leaveChannel({ force = false } = {}) {
        if (this.channel_type === "livechat" && this.channel_member_ids.length <= 2 && !force) {
            await this.askLeaveConfirmation(_t("Leaving will end the livechat. Proceed leaving?"));
        }
        super.leave();
    },
});
