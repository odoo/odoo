import { Thread } from "@mail/core/common/thread";

import { useListener } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useOnChange } from "@mail/utils/common/hooks";

/** @type {Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        useListener(
            this.scrollableRef,
            "scrollend",
            () => (this.state.scrollTop = this.scrollableRef().scrollTop)
        );
        useOnChange(
            () => [this.props.thread.loadNewer, this.state.mountedAndLoaded, this.state.scrollTop],
            (loadNewer, mountedAndLoaded, scrollTop) => {
                if (
                    loadNewer ||
                    !mountedAndLoaded ||
                    !this.channel?.self_member_id ||
                    !this.scrollableRef()
                ) {
                    return;
                }
                if (
                    Math.abs(
                        scrollTop +
                            this.scrollableRef().clientHeight -
                            this.scrollableRef().scrollHeight
                    ) <= 1
                ) {
                    this.channel.self_member_id.hideUnreadBanner = true;
                }
            }
        );
    },
    /** @override */
    applyScrollContextually(thread) {
        if (thread.channel?.self_member_id && thread.scrollUnread) {
            if (thread.firstUnreadMessage) {
                const messageEl = this.messageRefs.get(thread.firstUnreadMessage.id)?.();
                if (!messageEl) {
                    return;
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
        } else {
            super.applyScrollContextually(...arguments);
        }
    },
    /** @override */
    fetchInitialMessages() {
        if (this.channel?.self_member_id && this.props.thread.scrollUnread) {
            this.props.thread.loadAround({
                messageId: this.channel.self_member_id.new_message_separator,
            });
        } else {
            super.fetchInitialMessages();
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
