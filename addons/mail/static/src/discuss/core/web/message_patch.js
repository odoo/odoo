/* @odoo-module */

import { Message } from "@mail/core/common/message";
import "@mail/core/web/message_patch"; // dependency ordering
import { markEventHandled } from "@web/core/utils/misc";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    getAuthorText() {
        return this.hasOpenChatFeature() ? _t("Open chat") : super.getAuthorText();
    },
    hasAuthorClickable() {
        return (
            super.hasAuthorClickable() &&
            this.message.author.type !== "guest" &&
            this.message.originThread?.channel?.channel_type !== "chat"
        );
    },
    hasOpenChatFeature() {
        return this.hasAuthorClickable();
    },
    onClickAuthor(ev) {
        if (this.hasOpenChatFeature()) {
            markEventHandled(ev, "Message.ClickAuthor");
            this.threadService.openChat({ partnerId: this.message.author.id });
            return;
        }
        return super.onClickAuthor(ev);
    },
});
