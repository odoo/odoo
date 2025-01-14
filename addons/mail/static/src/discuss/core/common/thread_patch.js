import { Thread } from "@mail/core/common/thread";

import { useEffect, toRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
        useEffect(
            (loadNewer, mountedAndLoaded, unreadSynced) => {
                if (
                    loadNewer ||
                    unreadSynced || // just marked as unread (local and server state are synced)
                    !mountedAndLoaded ||
                    !this.props.thread.selfMember ||
                    !this.scrollableRef.el
                ) {
                    return;
                }
                const el = this.scrollableRef.el;
                if (Math.abs(el.scrollTop + el.clientHeight - el.scrollHeight) <= 1) {
                    this.props.thread.selfMember.hideUnreadBanner = true;
                }
            },
            () => [
                this.props.thread.loadNewer,
                this.state.mountedAndLoaded,
                this.props.thread.selfMember?.unreadSynced,
                this.state.scrollTop,
            ]
        );
    },
    /** @override */
    applyScrollContextually(thread) {
        if (thread.selfMember && thread.scrollUnread) {
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
            this.env.bus.trigger("scrollUnreadChanged");
        } else {
            super.applyScrollContextually(...arguments);
        }
    },
    /** @override */
    fetchMessages() {
        if (this.props.thread.selfMember && this.props.thread.scrollUnread) {
            toRaw(this.props.thread).loadAround(this.props.thread.selfMember.new_message_separator);
        } else {
            super.fetchMessages();
        }
    },
    get newMessageBannerText() {
        if (this.props.thread.selfMember?.totalUnreadMessageCounter > 1) {
            return _t("%s new messages", this.props.thread.selfMember.totalUnreadMessageCounter);
        }
        return _t("1 new message");
    },
    async onClickUnreadMessagesBanner() {
        await this.props.thread.loadAround(this.props.thread.selfMember.localNewMessageSeparator);
        this.messageHighlight?.highlightMessage(
            this.props.thread.firstUnreadMessage,
            this.props.thread
        );
    },
};
patch(Thread.prototype, threadPatch);
