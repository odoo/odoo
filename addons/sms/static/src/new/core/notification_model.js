/** @odoo-module */

import { Notification } from "@mail/new/core/notification_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Notification.prototype, "sms", {
    get icon() {
        if (this.notification_type === "sms") {
            return "fa fa-mobile";
        }
        return this._super();
    },
    get label() {
        if (this.notification_type === "sms") {
            return _t("SMS");
        }
        return this._super();
    },
});
