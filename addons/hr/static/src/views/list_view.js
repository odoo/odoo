import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";

import { useArchiveEmployee } from "@hr/views/archive_employee_hook";
import { patchHrEmployee } from "./patch_hr_employee";

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
            selectedRecords.map(({ resId }) => resId)
        );
        return menuItems;
    }

    async createRecord() {
        await this.props.createRecord();
    }
}

export class EmployeeListRenderer extends ListRenderer {
    static template = "hr.ListRenderer";
}
patchHrEmployee(EmployeeListRenderer);

registry.category("views").add("hr_employee_list", {
    ...listView,
    Controller: EmployeeListController,
    Renderer: EmployeeListRenderer,
});
