/** @odoo-module */

import { MessagingMenu } from "@mail/new/messaging_menu/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, "snailmail/messaging_menu", {
    openFailureView(failure) {
        if (failure.type !== "snail") {
            return this._super(failure);
        }
        this.env.services.action.doAction({
            name: _t("Snailmail Failures"),
            type: "ir.actions.act_window",
            view_mode: "kanban,list,form",
            views: [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            res_model: failure.resModel,
            domain: [["message_ids.snailmail_error", "=", true]],
        });
        this.close();
    },
});
