import { Component } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

export class KanbanDropdownMenuWrapper extends Component {
    static template = "web.KanbanDropdownMenuWrapper";
    static props = {
        slots: Object,
    };

    setup() {
        this.dropdownControl = useDropdownCloser();
    }

    onClick(ev) {
        this.dropdownControl.closeAll();
    }
}
