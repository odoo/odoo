import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

function mySubscriptionItem() {
    const action = usePlugin(ActionPlugin);
    return {
        type: "item",
        id: "mysubscription_user_menu",
        description: _t("My Subscription"),
        callback: () => {
            action.doAction("mysubscription.dashboard", {
                clearBreadcrumbs: true,
            });
        },
        sequence: 55,
    };
}

registry.category("user_menuitems").add("mysubscription_user_menu", mySubscriptionItem);
