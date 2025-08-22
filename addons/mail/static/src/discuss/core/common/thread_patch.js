import { Thread } from "@mail/core/common/thread";

import { useEffect, toRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        useEffect(
            (loadNewer, mountedAndLoaded) => {
                if (
                    loadNewer ||
                    !mountedAndLoaded ||
                    !this.props.thread.self_member_id ||
                    !this.scrollableRef.el
                ) {
                    return;
                }
                const el = this.scrollableRef.el;
                if (Math.abs(el.scrollTop + el.clientHeight - el.scrollHeight) <= 1) {
                    this.props.thread.self_member_id.hideUnreadBanner = true;
                }
            },
            () => [this.props.thread.loadNewer, this.state.mountedAndLoaded, this.state.scrollTop]
        );
    },
    /** @override */
    applyScrollContextually(thread) {
        if (thread.self_member_id && thread.scrollUnread) {
            if (thread.firstUnreadMessage) {
                const messageEl = this.refByMessageId.get(thread.firstUnreadMessage.id)?.el;
                if (!messageEl) {
                    return;
                }
                const messageCenter =
                    messageEl.offsetTop -
                    this.scrollableRef.el.offsetHeight / 2 +
                    messageEl.offsetHeight / 2;
                this.setScroll(messageCenter);
            } else {
                const scrollTop =
                    this.props.order === "asc"
                        ? this.scrollableRef.el.scrollHeight - this.scrollableRef.el.clientHeight
                        : 0;
                this.setScroll(scrollTop);
            }
            thread.scrollUnread = false;
            if (this.isAtBottom && !thread.markedAsUnread && thread.isFocused) {
                thread.markAsRead();
            }
        } else {
            super.applyScrollContextually(...arguments);
        }
    },
    /** @override */
    fetchMessages() {
        if (this.props.thread.self_member_id && this.props.thread.scrollUnread) {
            toRaw(this.props.thread).loadAround(
                this.props.thread.self_member_id.new_message_separator
            );
        } else {
            super.fetchMessages();
        }
    },
    get newMessageBannerText() {
        if (this.props.thread.self_member_id?.message_unread_counter > 1) {
            return _t("%s new messages", this.props.thread.self_member_id.message_unread_counter);
        }
        return _t("1 new message");
    },
    async onClickUnreadMessagesBanner() {
        await this.props.thread.loadAround(
            this.props.thread.self_member_id.new_message_separator_ui
        );
        this.messageHighlight?.highlightMessage(
            this.props.thread.firstUnreadMessage,
            this.props.thread
        );
    },
};
patch(Thread.prototype, threadPatch);
