/** @odoo-module */

import { NotificationGroup } from "@mail/core/common/notification_group_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(NotificationGroup.prototype, {
    get iconSrc() {
        if (this.type === "snail") {
            return "/snailmail/static/img/snailmail_failure.png";
        }
        return super.iconSrc;
    },
    get body() {
        if (this.type === "snail") {
            return _t("An error occurred when sending a letter with Snailmail.");
        }
        return super.body;
    },
});
