import { patch } from "@web/core/utils/patch";
import { EmployeeListController } from '@hr/views/list_view';
import { HrPresenceActionMenus } from "../search/hr_presence_action_menus/hr_presence_action_menus";

patch(EmployeeListController, {
    components: {
        ...EmployeeListController.components,
        ActionMenus: HrPresenceActionMenus,
    },
});
