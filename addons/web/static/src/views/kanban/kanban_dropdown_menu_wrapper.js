/** @odoo-module */

import { Component } from "@odoo/owl";
import { DROPDOWN } from "@web/core/dropdown/dropdown_behaviours/dropdown_nesting";

export class KanbanDropdownMenuWrapper extends Component {
    onClick(ev) {
        this.env[DROPDOWN].closeAllParents();
    }
}
KanbanDropdownMenuWrapper.template = "web.KanbanDropdownMenuWrapper";
KanbanDropdownMenuWrapper.props = {
    slots: Object,
};
