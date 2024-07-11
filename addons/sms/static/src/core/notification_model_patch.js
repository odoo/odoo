/** @odoo-module */

import { Notification } from "@mail/core/common/notification_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Notification.prototype, {
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
});
