import { fields } from "@mail/model/export";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.country_id = fields.One("res.country");
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
        if (this.channel?.channel_type === "livechat") {
            return Boolean(this.self_member_id);
        }
        return super.inChathubOnNewMessage;
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
            this.channel.self_member_id &&
            !this.livechat_end_dt
        ) {
            this.store.env.services.dialog.add(MessageConfirmDialog, {
                message: this.newestPersistentOfAllMessage,
                confirmText: _t("Leave Conversation"),
                onConfirm: async () => await super.leaveChannel(...arguments),
                prompt: _t("Here's the most recent message:"),
                size: "xl",
                title: _t(
                    "Leaving will end the live chat with %(channel_name)s. Are you sure you want to continue?",
                    { channel_name: this.displayName }
                ),
            });
        } else {
            await super.leaveChannel(...arguments);
        }
    },
});
