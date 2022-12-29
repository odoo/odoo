/** @odoo-module */

import { NotificationGroup } from "@mail/new/core/notification_group_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(NotificationGroup.prototype, "sms/notification_group_model", {
    get iconSrc() {
        if (this.type === "sms") {
            return "/sms/static/img/sms_failure.svg";
        }
        return this._super();
    },
    get body() {
        if (this.type === "sms") {
            return _t("An error occurred when sending an SMS");
        }
        return this._super();
    },
});
