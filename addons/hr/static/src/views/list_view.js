/** @odoo-module native */
import { useArchiveEmployee } from "@hr/views/archive_employee_hook";
import { registry } from "@web/core/registry";
import { ListController, listView } from "@web/views/list";

export class EmployeeListController extends ListController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const selectedRecords = this.model.root.selection;

        menuItems.archive.callback = this.archiveEmployee.bind(
            this,
            selectedRecords.map(({ resId }) => resId),
        );
        return menuItems;
    }
}

registry.category("views").add("hr_employee_list", {
    ...listView,
    Controller: EmployeeListController,
});
