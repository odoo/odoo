import { Thread } from "@mail/core/common/thread";

import { toRaw } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    /** @override */
    fetchMessages() {
        if (this.props.thread.selfMember && this.props.thread.scrollUnread) {
            toRaw(this.props.thread).loadAround(this.props.thread.selfMember.new_message_separator);
        } else {
            super.fetchMessages();
        }
    },
    /** @override */
    isDisplayedOnUpdate() {
        super.isDisplayedOnUpdate(...arguments);
        if (this.selfMember && !this.isDisplayed) {
            this.selfMember.syncUnread = true;
        }
    },
};
patch(Thread.prototype, threadPatch);
