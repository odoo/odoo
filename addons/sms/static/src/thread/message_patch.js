import { usePlugin } from "@odoo/owl";

import { ORM } from "@web/core/orm_plugin";
import { user } from "@web/core/user";
import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = usePlugin(ORM);
    },
    async onClickNotification(ev) {
        const hasAccountFailure = this.message.notification_ids.some(
            (notification) => notification.isFailure && notification.failure_type === "sms_acc"
        );
        if (
            this.message.message_type === "sms" &&
            hasAccountFailure &&
            (await user.hasGroup("base.group_system"))
        ) {
            const [accountId] = await this.orm.call("iap.account", "get", [], {
                service_name: "sms",
                force_create: false,
            });
            if (accountId) {
                const action = await this.orm.call("iap.account", "action_manage", [accountId]);
                this.env.services.action.doAction(action);
            }
        }

        super.onClickNotification(ev);
    },
});
