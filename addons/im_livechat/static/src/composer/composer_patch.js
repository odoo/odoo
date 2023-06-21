/* @odoo-module */

import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, "im_livechat", {
    get allowUpload() {
        return this.thread?.type !== "livechat" && this._super();
    },

    onKeydown(ev) {
        this._super(ev);
        if (
            ev.key === "Tab" &&
            this.thread?.type === "livechat" &&
            !this.props.composer.textInputContent
        ) {
            const threadChanged = this.threadService.goToOldestUnreadLivechatThread();
            if (threadChanged) {
                // prevent chat window from switching to the next thread: as
                // we want to go to the oldest unread thread, not the next
                // one.
                ev.stopPropagation();
            }
        }
    },

    displayNextLivechatHint() {
        return (
            this.thread?.type === "livechat" &&
            !this.env.inChatWindow &&
            Object.values(this.store.discuss.livechat.threads).some((localId) => {
                return localId !== this.thread.localId && this.store.threads[localId].isUnread;
            })
        );
    },
});
