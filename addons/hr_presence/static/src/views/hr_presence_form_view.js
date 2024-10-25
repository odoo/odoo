/** @odoo-module */

import { registry } from "@web/core/registry";

import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { HrPresenceCogMenu } from "../search/hr_presence_cog_menu/hr_presence_cog_menu";


export class EmployeeFormController extends FormController {
    static components = {
        ...FormController.components,
        CogMenu: HrPresenceCogMenu,
    };
}

registry.category("views").add("hr_employee_form", {
    ...formView,
    Controller: EmployeeFormController,
});
