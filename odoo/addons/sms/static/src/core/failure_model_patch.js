/** @odoo-module */

import { Failure } from "@mail/core/common/failure_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Failure.prototype, {
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
