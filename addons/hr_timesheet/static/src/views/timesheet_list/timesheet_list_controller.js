/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";

export class TimesheetListController extends ListController {

    get actionMenuItems() {
        const actionMenus = super.actionMenuItems;
        // hack so we don't show WIP print report timesheet app
        const { print, action } = actionMenus;
        return {
            action: action,
            print: print.filter((a) => a.name !== this.env._t("WIP report")),
        };
    }

}
