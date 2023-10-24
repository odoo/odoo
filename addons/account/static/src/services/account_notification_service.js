/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";


export const accountNotificationService = {
    dependencies: ["bus_service", "notification", "action"],

    start(env, { bus_service, notification, action }) {
        bus_service.subscribe("account_notification", ({ message, sticky, title, type, action_button}) => {
            const buttons = [{
                name: action_button.name,
                primary: false,
                onClick: () => {
                    action.doAction({
                        name: _t(action_button.action_name),
                        type: 'ir.actions.act_window',
                        res_model: action_button.model,
                        domain: [["id", "in", action_button.res_ids]],
                        views: [[false, 'list'], [false, 'form']],
                        target: 'current',
                    });
                },
            }];
            notification.add(message, { sticky, title, type, buttons });
        });
    }
};

registry.category("services").add("accountNotification", accountNotificationService);
