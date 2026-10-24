import { usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

registry.category("actions").add("crm_sale_project_top_menu_opportunity", (clientAction) => {
    const actionService = usePlugin(ActionPlugin);
    actionService.doAction(clientAction.params.action);
});
