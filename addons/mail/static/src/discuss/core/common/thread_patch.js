import { Thread } from "@mail/core/common/thread";
import { UNREAD_COUNTER_LIMIT } from "@mail/discuss/core/common/channel_member_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {Thread} */
const threadPatch = {
    /** @override */
    applyScrollContextually(thread) {
        if (thread.channel?.self_member_id && thread.scrollUnread) {
            if (thread.firstUnreadMessage) {
                const messageEl = this.messageRefs.get(thread.firstUnreadMessage.id)?.();
                if (!messageEl) {
                    return false;
                }
                const messageCenter =
                    messageEl.offsetTop -
                    this.scrollableRef().offsetHeight / 2 +
                    messageEl.offsetHeight / 2;
                this.setScroll(messageCenter);
            } else {
                const scrollTop =
                    this.props.order === "asc"
                        ? this.scrollableRef().scrollHeight - this.scrollableRef().clientHeight
                        : 0;
                this.setScroll(scrollTop);
            }
            thread.scrollUnread = false;
            if (this.shouldMarkAsReadOnScroll(thread)) {
                thread.markAsRead();
            }
            return true;
        } else {
            return super.applyScrollContextually(...arguments);
        }
    },
    get newMessageBannerText() {
        const counter = this.channel?.self_member_id?.message_unread_counter;
        if (counter > 1) {
            return _t("%s new messages", counter >= UNREAD_COUNTER_LIMIT ? "99+" : counter);
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
