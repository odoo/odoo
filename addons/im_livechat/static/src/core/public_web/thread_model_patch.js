import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.country_id = fields.One("res.country");
    },
    _computeDiscussAppCategory() {
        if (this.channel?.channel_type !== "livechat") {
            return super._computeDiscussAppCategory();
        }
        return (
            this.channel.livechat_channel_id?.appCategory ??
            this.channel.appAsLivechats?.defaultLivechatCategory
        );
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
        if (this.channel?.channel_type === "livechat" && !correspondent) {
            return this.livechatVisitorMember;
        }
        return correspondent;
    },

    get inChathubOnNewMessage() {
        return this.channel?.channel_type === "livechat" || super.inChathubOnNewMessage;
    },

    /**
     * @override
     * @param {boolean} pushState
     */
    setAsDiscussThread(pushState) {
        super.setAsDiscussThread(pushState);
        if (this.store.env.services.ui.isSmall && this.channel?.channel_type === "livechat") {
            this.store.discuss.activeTab = "livechat";
        }
    },
    async leaveChannel() {
        if (
            this.channel?.channel_type === "livechat" &&
            this.channel?.channel_member_ids.length <= 2 &&
            !this.livechat_end_dt
        ) {
            await this.askLeaveConfirmation(
                _t("Leaving will end the live chat. Do you want to proceed?")
            );
        }
        super.leaveChannel(...arguments);
    },
});
