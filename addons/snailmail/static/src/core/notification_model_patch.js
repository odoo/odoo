import { Notification } from "@mail/core/common/notification_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/** @type {import("models").Notification} */
const notificationPatch = {
    get icon() {
        if (this.notification_type === "snail") {
            return "fa fa-paper-plane";
        }
        return super.icon;
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
        return super.statusIcon;
    },
    get failureMessage() {
        switch (this.failure_type) {
            case "sn_credit":
                return _t("Snailmail Credit Error");
            case "sn_trial":
                return _t("Snailmail Trial Error");
            case "sn_price":
                return _t("Snailmail No Price Available");
            case "sn_fields":
                return _t("Snailmail Missing Required Fields");
            case "sn_format":
                return _t("Snailmail Format Error");
            case "sn_error":
                return _t("Snailmail Unknown Error");
            default:
                return super.failureMessage;
        }
    },
    get statusTitle() {
        if (this.notification_type === "snail") {
            switch (this.notification_status) {
                case "sent":
                    return _t("Sent");
                case "ready":
                    return _t("Awaiting Dispatch");
                case "canceled":
                    return _t("Cancelled");
                default:
                    return _t("Error");
            }
        }
        return super.statusTitle;
    },
};
patch(Notification.prototype, notificationPatch);
