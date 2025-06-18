import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';

import { useArchiveEmployee } from '@hr/views/archive_employee_hook';

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
            selectedRecords.map(({resId}) => resId),
        )
        return menuItems;
    }

    async createRecord() {
        await this.props.createRecord();
    }
}

registry.category('views').add('hr_employee_list', {
    ...listView,
    Controller: EmployeeListController,
});
