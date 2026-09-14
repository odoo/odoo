/** @odoo-module native */
import { patch } from "@web/core/utils/patch";
import { EmployeeFormController } from "@hr/views/form_view";
import { withPresenceSubMenu } from "./presence_action_items.js";

patch(EmployeeFormController, {
    components: {
        ...EmployeeFormController.components,
        CogMenu: withPresenceSubMenu(EmployeeFormController.components.CogMenu),
    },
});
