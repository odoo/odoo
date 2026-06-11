import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

function mySubscriptionItem(env) {
    return {
        type: "item",
        id: "mysubscription_user_menu",
        description: _t("My Subscription"),
        callback: () => {
            const actionService = env.services.action;
            actionService.doAction({
                type: "ir.actions.client",
                tag: "mysubscription.dashboard",
            }, {
                clearBreadcrumbs: true,
            });
        },
        sequence: 55,
    };
}

registry.category("user_menuitems").add("mysubscription_user_menu", mySubscriptionItem);
