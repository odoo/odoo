import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { useService } from "@web/core/utils/hooks";

export class ActionList extends Component {
    static components = { Dropdown, DropdownItem };
    static props = [
        "inline?",
        "dropdown?",
        "quick?",
        "group?",
        "other?",
        "odooControlPanelSwitchStyle?",
        "thread?",
    ];
    static template = "mail.ActionList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
    }
}
