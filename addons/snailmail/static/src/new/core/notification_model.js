/** @odoo-module */

import { Notification } from "@mail/new/core/notification_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(Notification.prototype, "snailmail", {
    get icon() {
        if (this.notification_type === "snail") {
            return "fa fa-paper-plane";
        }
        return this._super();
    },

    get statusIcon() {
        if (this.notification_type === "snail") {
            switch (this.notification_status) {
                case "sent":
                    return "fa fa-check";
                case "ready":
                    return "fa fa-clock-o";
                case "canceled":
                    return "fa fa-trash-o";
                default:
                    return "fa fa-exclamation text-danger";
            }
        }
        return this._super();
    },

    get statusTitle() {
        if (this.notification_type === "snail") {
            switch (this.notification_status) {
                case "sent":
                    return _t("Sent");
                case "ready":
                    return _t("Awaiting Dispatch");
                case "canceled":
                    return _t("Canceled");
                default:
                    return _t("Error");
            }
        }
        return this._super();
    },
});
