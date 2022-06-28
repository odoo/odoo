/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class StatusBarButtons extends Component {
    get visibleSlotNames() {
        return Object.entries(this.props.slots)
            .filter(
                (entry) => entry[1].isVisible && (entry[1].displayInReadOnly ? this.props.readonly : true)
            )
            .map((entry) => entry[0]);
    }
}
StatusBarButtons.template = "web.StatusBarButtons";
StatusBarButtons.components = {
    Dropdown,
    DropdownItem,
};
