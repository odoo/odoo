import { BusPlugin } from "@bus/services/bus_plugin";
import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class AccountNotificationPlugin extends Plugin {
    action = usePlugin(ActionPlugin);
    bus = usePlugin(BusPlugin);
    notification = usePlugin(NotificationPlugin);

    setup() {
        const unsubscribe = this.bus.subscribe(
            "account_notification",
            ({ message, sticky, title, type, action_button }) => {
                const buttons = [
                    {
                        name: action_button.name,
                        primary: false,
                        onClick: () => {
                            this.action.doAction({
                                name: _t(action_button.action_name),
                                type: "ir.actions.act_window",
                                res_model: action_button.model,
                                domain: [["id", "in", action_button.res_ids]],
                                views: [
                                    [false, "list"],
                                    [false, "form"],
                                ],
                                target: "current",
                            });
                        },
                    },
                ];
                this.notification.add(message, { sticky, title, type, buttons });
            }
        );

        onWillDestroy(unsubscribe);
    }
}

services.add(AccountNotificationPlugin);
