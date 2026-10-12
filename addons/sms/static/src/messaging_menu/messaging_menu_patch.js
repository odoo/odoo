import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {MessagingMenu} */
const messagingMenuPatch = {
    openFailureView(failure, options) {
        if (failure.type === "email") {
            return super.openFailureView(...arguments);
        }
        this.env.services.action.doAction(
            {
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
            },
            { newWindow: options?.isMiddleClick }
        );
        this.close?.();
    },
    getFailureNotificationName(failure) {
        if (failure.type === "sms") {
            return _t("SMS Failure: %(modelName)s", { modelName: failure.modelName });
        }
        return super.getFailureNotificationName(...arguments);
    },
};
patch(MessagingMenu.prototype, messagingMenuPatch);
