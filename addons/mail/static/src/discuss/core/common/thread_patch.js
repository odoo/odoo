import { Thread } from "@mail/core/common/thread";

import { toRaw } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

/** @type {Thread} */
const threadPatch = {
    /** @override */
    fetchMessages() {
        if (this.props.thread.selfMember && this.props.thread.scrollUnread) {
            toRaw(this.props.thread).loadAround(this.props.thread.selfMember.new_message_separator);
        } else {
            super.fetchMessages();
        }
    },
};
patch(Thread.prototype, threadPatch);
