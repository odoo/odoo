/** @odoo-module **/

import { useArchiveEmployee } from "@hr/views/archive_employee_hook";

import { useOpenChat } from "@mail/new/common/open_chat_hook";

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { formView } from "@web/views/form/form_view";

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getActionMenuItems() {
        const menuItems = super.getActionMenuItems();
        if (!this.archiveEnabled || !this.model.root.isActive) {
            return menuItems;
        }

        const archiveAction = menuItems.other.find((item) => item.key === "archive");
        if (archiveAction) {
            archiveAction.callback = this.archiveEmployee.bind(this, this.model.root.resId);
        }
        return menuItems;
    }
}

// TODO KBA: to remove in master
export class EmployeeFormRenderer extends FormRenderer {
    setup() {
        super.setup();
        this.openChat = useOpenChat(this.props.record.resModel);
    }
}

registry.category("views").add("hr_employee_form", {
    ...formView,
    Controller: EmployeeFormController,
    Renderer: EmployeeFormRenderer,
});
