/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useSignViewButtons } from "@sign/views/hooks";
import { Dropdown, DropdownItem } from "@web/core/dropdown/dropdown";

export class SignKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }
}
SignKanbanController.components = {
    ...KanbanController.components,
    Dropdown,
    DropdownItem,
};

SignKanbanController.template = "sign.SignKanbanController";
