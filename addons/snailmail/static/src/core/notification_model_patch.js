import { Notification } from "@mail/core/common/notification_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/** @type {import("models").Notification} */
const notificationPatch = {
    get icon() {
        if (this.notification_type === "snail") {
            return "send";
        }
        return super.icon;
    },

    get statusIcon() {
        if (this.notification_type === "snail") {
            switch (this.notification_status) {
                case "sent":
                    return "check";
                case "ready":
                    return "schedule";
                case "canceled":
                    return "delete";
                default:
                    return "priority_high";
            }
        }
        return super.statusIcon;
    },
    get statusIconClass() {
        if (["sent", "ready", "canceled"].includes(this.notification_status)) {
            return "text-danger";
        }
    },
    get failureMessage() {
        switch (this.failure_type) {
            case "sn_credit":
                return _t("Insufficient Credits");
            case "sn_trial":
                return _t("No IAP Credits");
            case "sn_price":
                return _t("Country Not Supported");
            case "sn_fields":
                return _t("Missing Required Fields");
            case "sn_format":
                return _t("Format Error");
            case "sn_error":
                return _t("Unknown Error");
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
