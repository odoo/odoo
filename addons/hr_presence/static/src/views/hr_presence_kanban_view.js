import { patch } from "@web/core/utils/patch";
import { EmployeeKanbanController } from '@hr/views/kanban_view';
import { HrPresenceActionMenus } from "../search/hr_presence_action_menus/hr_presence_action_menus";

patch(EmployeeKanbanController, {
    components: {
        ...EmployeeKanbanController.components,
        ActionMenus: HrPresenceActionMenus,
    },
});
