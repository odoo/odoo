/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { patch } from '@web/core/utils/patch';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';

import { ArchiveEmployeeMixin } from '../mixins/archive_employee_mixin';

export class EmployeeListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService('action');
    }

    getActionMenuItems() {
        const menuItems = super.getActionMenuItems();
        const selectedRecords = this.model.root.selection;

        // Only override the Archive action when only 1 record is selected.
        if (!this.archiveEnabled || selectedRecords.length > 1 || !selectedRecords[0].data.active) {
            return menuItems;
        }

        const archiveAction = menuItems.other.find((item) => item.key === "archive");
        if (archiveAction) {
            archiveAction.callback = () => {
                const archiveAction = this._openArchiveEmployee(this.model.root.resId);
                this.actionService.doAction(archiveAction, {
                    onClose: async () => {
                        await this.model.load();
                        this.model.notify();
                    }
                });
            };
        }
        return menuItems;
    }
}
patch(EmployeeListController.prototype, 'employee_list_controller_archive_mixin', ArchiveEmployeeMixin);

registry.category('views').add('hr_employee_list', {
    ...listView,
    Controller: EmployeeListController,
});
