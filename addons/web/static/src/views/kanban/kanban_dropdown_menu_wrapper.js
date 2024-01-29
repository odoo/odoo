import { Component } from "@odoo/owl";
import { DROPDOWN } from "@web/core/dropdown/dropdown";

export class KanbanDropdownMenuWrapper extends Component {
    static template = "web.KanbanDropdownMenuWrapper";
    static props = {
        slots: Object,
    };

    onClick(ev) {
        this.env[DROPDOWN].closeAllParents();
    }
}
