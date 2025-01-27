/** @odoo-module */

import { Failure } from "@mail/core/common/failure_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Failure.prototype, {
    get iconSrc() {
        if (this.type === "snail") {
            return "/snailmail/static/img/snailmail_failure.png";
        }
        return super.iconSrc;
    },
    get body() {
        if (this.type === "snail") {
            if (this.notifications.length === 1 && this.lastMessage?.thread) {
                return _t(
                    "An error occurred when sending a letter with Snailmail on “%(record_name)s”",
                    { record_name: this.lastMessage.thread.name }
                );
            }
            return _t("An error occurred when sending a letter with Snailmail.");
        }
        return super.body;
    },
});
