import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    async onClickNotification(ev) {
        const hasAccountFailure = this.message.notification_ids.some(
            (notification) => notification.isFailure && notification.failure_type === "sms_acc"
        );
        if (
            this.message.message_type === "sms" &&
            hasAccountFailure &&
            (await user.hasGroup("base.group_system"))
        ) {
            const [accountId] = await this.env.services.orm.call("iap.account", "get", [], {
                service_name: "sms",
                force_create: false,
            });
            if (accountId) {
                this.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    name: _t("SMS Account"),
                    target: "current",
                    res_model: "iap.account",
                    res_id: accountId,
                    views: [[false, "form"]],
                });
                return;
            }
        }

        super.onClickNotification(ev);
    },
});
