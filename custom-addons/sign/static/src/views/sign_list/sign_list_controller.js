/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useSignViewButtons } from "@sign/views/hooks";
import { Dropdown, DropdownItem } from "@web/core/dropdown/dropdown";

export class SignListController extends ListController {
    setup() {
        super.setup(...arguments);
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }
}
SignListController.components = {
    ...ListController.components,
    Dropdown,
    DropdownItem,
};

SignListController.template = "sign.SignListController";
