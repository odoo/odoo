import { Notification } from "@mail/core/common/notification_model";
import { patchModel } from "@mail/model/export";
import { _t } from "@web/core/l10n/translation";

export const notificationPatch = patchModel(Notification, {
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
});
