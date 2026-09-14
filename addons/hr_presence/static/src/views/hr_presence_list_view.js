/** @odoo-module native */
import { patch } from "@web/core/utils/patch";
import { EmployeeListController } from "@hr/views/list_view";
import { withPresenceSubMenu } from "./presence_action_items.js";

patch(EmployeeListController, {
    components: {
        ...EmployeeListController.components,
        ActionMenus: withPresenceSubMenu(EmployeeListController.components.ActionMenus),
    },
});
