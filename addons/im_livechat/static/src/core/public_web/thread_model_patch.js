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
    get allowedToLeaveChannelTypes() {
        return [...super.allowedToLeaveChannelTypes, "livechat"];
    },
    get correspondents() {
        return super.correspondents.filter(
            (correspondent) => correspondent.livechat_member_type !== "bot"
        );
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
        super.leaveChannel(...arguments);
    },
});
