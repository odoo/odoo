/** @odoo-module */

import { NotificationGroup } from "@mail/core/common/notification_group_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(NotificationGroup.prototype, {
    get iconSrc() {
        if (this.type === "sms") {
            return "/sms/static/img/sms_failure.svg";
        }
        return super.iconSrc;
    },
    get body() {
        if (this.type === "sms") {
            return _t("An error occurred when sending an SMS");
        }
        return super.body;
    },
});
