/** @odoo-module */

import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';
import { HrPresenceActionMenus } from "../search/hr_presence_action_menus/hr_presence_action_menus";


export class EmployeeListController extends ListController {
    static components = {
        ...ListController.components,
        ActionMenus: HrPresenceActionMenus,
    };
}

registry.category('views').add('hr_employee_list', {
    ...listView,
    Controller: EmployeeListController,
});
