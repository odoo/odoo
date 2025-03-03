import { Notification } from "@mail/core/common/notification_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Notification} */
const notificationPatch = {
    get failureMessage() {
        switch (this.failure_type) {
            case "sms_number_missing":
                return _t("Missing Number");
            case "sms_number_format":
                return _t("Wrong Number Format");
            case "sms_credit":
                return _t("Insufficient Credit");
            case "sms_country_not_supported":
                return _t("Country Not Supported");
            case "sms_registration_needed":
                return _t("Country-specific Registration Required");
            case "sms_server":
                return _t("Server Error");
            case "sms_acc":
                return _t("Unregistered Account");
            case "sms_expired":
                return _t("Expired");
            case "sms_invalid_destination":
                return _t("Invalid Destination");
            case "sms_not_allowed":
                return _t("Not Allowed");
            case "sms_not_delivered":
                return _t("Not Delivered");
            case "sms_rejected":
                return _t("Rejected");
            default:
                return super.failureMessage;
        }
    },
    get icon() {
        if (this.notification_type === "sms") {
            return "fa fa-mobile";
        }
        return super.icon;
    },
    get label() {
        if (this.notification_type === "sms") {
            return _t("SMS");
        }
        return super.label;
    },
};
patch(Notification.prototype, notificationPatch);
