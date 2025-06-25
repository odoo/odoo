/** @odoo-module */

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    openFailureView(failure) {
        if (failure.type === "email") {
            return super.openFailureView(failure);
        }
        this.env.services.action.doAction({
            name: _t("SMS Failures"),
            type: "ir.actions.act_window",
            view_mode: "kanban,list,form",
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            res_model: failure.resModel,
            domain: [["message_has_sms_error", "=", true]],
            context: { create: false },
        });
        this.dropdown.close();
    },
    getFailureNotificationName(failure) {
        if (failure.type === "sms") {
            return _t("SMS Failure: %(modelName)s", { modelName: failure.modelName });
        }
        return super.getFailureNotificationName(...arguments);
    },
});
