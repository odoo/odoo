/* @odoo-module */

import { Message } from "@mail/core/common/message";
import "@mail/core/web/message_patch"; // dependency ordering
import { markEventHandled } from "@web/core/utils/misc";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, "discuss/core/web", {
    getAuthorText() {
        return this.hasOpenChatFeature() ? _t("Open chat") : this._super();
    },
    hasAuthorClickable() {
        return (
            this._super() &&
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
        return this._super(ev);
    },
});
