/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { FormController } from '@web/views/form/form_controller';

export class ProjectTaskFormController extends FormController {
    setup() {
        super.setup();
        this.taskRecurrence = useService('project_task_recurrence');
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (this.model.root.data.recurrence_id) {
            menuItems.archive.callback = () =>
                this.taskRecurrence.addressRecurrence([this.model.root], "archive", () =>
                    this.model.root.archive()
                );
        }
        return menuItems;
    }

    deleteRecord() {
        this.taskRecurrence.addressRecurrence(
            [this.model.root],
            'delete',
            () => {
                this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            }
        );
    }
}
