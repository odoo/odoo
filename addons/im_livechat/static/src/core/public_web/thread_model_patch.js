import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.appAsLivechats = fields.One("DiscussApp", {
            compute() {
                return this.channel?.channel_type === "livechat" ? this.store.discuss : null;
            },
        });
        this.country_id = fields.One("res.country");
        this.livechat_channel_id = fields.One("im_livechat.channel", { inverse: "threads" });
    },
    _computeDiscussAppCategory() {
        if (this.channel?.channel_type !== "livechat") {
            return super._computeDiscussAppCategory();
        }
        return (
            this.livechat_channel_id?.appCategory ?? this.appAsLivechats?.defaultLivechatCategory
        );
    },
    get hasMemberList() {
        return this.channel?.channel_type === "livechat" || super.hasMemberList;
    },
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    get correspondents() {
        return super.channel?.correspondents.filter(
            (correspondent) => correspondent.livechat_member_type !== "bot"
        );
    },

    computeCorrespondent() {
        const correspondent = super.computeCorrespondent();
        if (this.channel?.channel_type === "livechat" && !correspondent) {
            return this.livechatVisitorMember;
        }
        return correspondent;
    },

    get displayName() {
        if (
            this.channel?.channel_type !== "livechat" ||
            !this.channel?.correspondent ||
            this.channel?.selfMember?.custom_channel_name
        ) {
            return super.displayName;
        }
        if (!this.channel?.correspondent.persona.is_public && this.channel?.correspondent.persona.country) {
            return `${this.channel?.correspondent.name} (${this.channel?.correspondent.persona.country.name})`;
        }
        if (this.country_id) {
            return `${this.channel?.correspondent.name} (${this.country_id.name})`;
        }
        return this.channel?.correspondent.name;
    },

    get avatarUrl() {
        if (this.channel?.channel_type === "livechat" && this.channel?.correspondent) {
            return this.channel?.correspondent.persona.avatarUrl;
        }
        return super.avatarUrl;
    },

    /**
     * @override
     * @param {boolean} pushState
     */
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        if (this.store.env.services.ui.isSmall && this.channel.channel_type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
    },
    async leaveChannel({ force = false } = {}) {
        if (this.channel?.channel_type === "livechat" && this.channel?.channel_member_ids.length <= 2 && !force) {
            await this.askLeaveConfirmation(_t("Leaving will end the livechat. Proceed leaving?"));
        }
        super.leaveChannel(...arguments);
    },
});
