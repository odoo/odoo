import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.appAsLivechats = fields.One("DiscussApp", {
            compute() {
                return this.channel_type === "livechat" ? this.store.discuss : null;
            },
        });
        this.country_id = fields.One("res.country");
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "threads" });
    },
    _computeDiscussAppCategory() {
        if (this.channel_type !== "livechat") {
            return super._computeDiscussAppCategory();
        }
        return (
            this.livechat_channel_id?.appCategory ?? this.appAsLivechats?.defaultLivechatCategory
        );
    },
    get hasMemberList() {
        return this.channel_type === "livechat" || super.hasMemberList;
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    get correspondents() {
        return super.correspondents.filter(
            (correspondent) => correspondent.livechat_member_type !== "bot"
        );
    },

    computeCorrespondent() {
        const correspondent = super.computeCorrespondent();
        if (this.channel_type === "livechat" && !correspondent) {
            return this.livechatVisitorMember;
        }
        return correspondent;
    },

    get displayName() {
        if (
            this.channel_type !== "livechat" ||
            !this.correspondent ||
            this.self_member_id?.custom_channel_name
        ) {
            return super.displayName;
        }
        if (!this.correspondent.persona.is_public && this.correspondent.persona.country) {
            return `${this.correspondent.name} (${this.correspondent.persona.country.name})`;
        }
        if (this.country_id) {
            return `${this.correspondent.name} (${this.country_id.name})`;
        }
        return this.correspondent.name;
    },

    get avatarUrl() {
        if (this.channel_type === "livechat" && this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },

    get inChathubOnNewMessage() {
        return this.channel_type === "livechat" || super.inChathubOnNewMessage;
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
        if (
            this.channel_type === "livechat" &&
            this.channel_member_ids.length <= 2 &&
            !this.livechat_end_dt &&
            !force
        ) {
            await this.askLeaveConfirmation(
                _t("Leaving will end the live chat. Do you want to proceed?")
            );
        }
        super.leaveChannel(...arguments);
    },
});
