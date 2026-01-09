import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class TimeOffNewDropdown extends Component{
    static template = "hr_holidays.TimeOffNewDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        onNewTimeOffRequest: Function,
        onNewAllocationRequest: Function,
    }

}
