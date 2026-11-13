import { Thread } from "@mail/core/common/thread";

import { computed } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        const scrollTarget = this.scrollTarget;
        this.scrollTarget = computed(() => {
            if (this.channel?.self_member_id && this.props.thread.scrollUnread) {
                const firstUnreadMessage = this.props.thread.firstUnreadMessage;
                return firstUnreadMessage ? { key: firstUnreadMessage.id } : { end: true };
            }
            return scrollTarget();
        });
    },
    /** @override */
    onScrollTargetReached() {
        super.onScrollTargetReached(...arguments);
        const thread = this.props.thread;
        if (this.channel?.self_member_id && thread.scrollUnread) {
            thread.scrollUnread = false;
            if (this.shouldMarkAsReadOnScroll(thread)) {
                thread.markAsRead();
            }
        }
    },
    get newMessageBannerText() {
        if (this.channel?.self_member_id?.message_unread_counter > 1) {
            return _t("%s new messages", this.channel.self_member_id.message_unread_counter);
        }
        return _t("1 new message");
    },
    async onClickUnreadMessagesBanner() {
        await this.props.thread.loadAround({
            messageId: this.channel.self_member_id.new_message_separator_ui,
        });
        this.messageHighlight?.highlightMessage(this.props.thread.firstUnreadMessage);
    },
};
patch(Thread.prototype, threadPatch);
