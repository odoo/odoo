/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { patch } from '@web/core/utils/patch';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';
import { FormRenderer } from '@web/views/form/form_renderer';

import { ArchiveEmployeeMixin } from '../mixins/archive_employee_mixin';
import { EmployeeChatMixin } from '../mixins/chat_mixin';

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService('action');
    }

    getActionMenuItems() {
        const menuItems = super.getActionMenuItems();
        if (!this.archiveEnabled || !this.model.root.isActive) {
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
patch(EmployeeFormController.prototype, 'employee_form_controller_archive_mixin', ArchiveEmployeeMixin);

export class EmployeeFormRenderer extends FormRenderer {}
patch(EmployeeFormRenderer.prototype, 'employee_form_renderer_mixin', EmployeeChatMixin);

registry.category('views').add('hr_employee_form', {
    ...formView,
    Controller: EmployeeFormController,
    Renderer: EmployeeFormRenderer,
});
