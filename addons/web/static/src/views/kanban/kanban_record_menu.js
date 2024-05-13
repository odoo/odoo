import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { Component } from "@odoo/owl";

export class KanbanRecordMenu extends Component {
    static template = "web.KanbanRecordMenu";
    static components = {
        Dropdown,
    };
    static props = {
        slots: Object,
    };

    setup() {
        this.state = useDropdownState();
    }

    onClick(ev) {
        this.state.close();
    }
}
