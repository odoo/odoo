import { Notification } from "@mail/core/common/notification_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Notification} */
const notificationPatch = {
    get failureMessage() {
        switch (this.failure_type) {
            case "twilio_authentication":
                return _t("Authentication Error");
            case "twilio_callback":
                return _t("Incorrect callback URL");
            case "twilio_from_missing":
                return _t("Missing From Number");
            case "twilio_from_to":
                return _t("From / To identic");
            case "twilio_wrong_credentials":
                return _t("Twilio Wrong Credentials");
            default:
                return super.failureMessage;
        }
    },
};
patch(Notification.prototype, notificationPatch);
