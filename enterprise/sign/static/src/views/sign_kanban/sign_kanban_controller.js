/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useSignViewButtons } from "@sign/views/hooks";
import { Dropdown, DropdownItem } from "@web/core/dropdown/dropdown";

export class SignKanbanController extends KanbanController {
    static template = "sign.SignKanbanController";
    static components = {
        ...KanbanController.components,
        Dropdown,
        DropdownItem,
    };

    setup() {
        super.setup(...arguments);
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }
}
