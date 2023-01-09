/** @odoo-module */

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';
import { FormRenderer } from '@web/views/form/form_renderer';

import { useArchiveEmployee } from '@hr/views/archive_employee_hook';
import { useOpenChat } from "@mail/views/open_chat_hook";

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        menuItems.archive.callback = this.archiveEmployee.bind(this, this.model.root.resId);
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

registry.category('views').add('hr_employee_form', {
    ...formView,
    Controller: EmployeeFormController,
    Renderer: EmployeeFormRenderer,
});
