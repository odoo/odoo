/* @odoo-module */

import { ThreadIcon } from "@mail/new/discuss/thread_icon";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ThreadIcon.prototype, "hr_holidays", {
    get classNames() {
        if (this.thread.type === "chat" && this.chatPartner.im_status === "leave_online") {
            return "o-mail-thread-icon-online fa-plane";
        }
        if (this.thread.type === "chat" && this.chatPartner.im_status === "leave_away") {
            return "o-mail-thread-icon-away fa-plane text-warning";
        }
        if (this.thread.type === "chat" && this.chatPartner.im_status === "leave_offline") {
            return "o-mail-thread-icon-offline fa-plane";
        }
        return this._super();
    },
    get titleText() {
        if (this.thread.type === "chat" && this.chatPartner.im_status === "leave_online") {
            return _t("Online");
        }
        if (this.thread.type === "chat" && this.chatPartner.im_status === "leave_away") {
            return _t("Idle");
        }
        if (this.thread.type === "chat" && this.chatPartner.im_status === "leave_offline") {
            return _t("Out of office");
        }
        return this._super();
    },
});
