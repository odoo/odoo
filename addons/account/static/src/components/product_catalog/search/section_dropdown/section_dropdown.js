import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class SectionDropdown extends Component {
    static template = "account.SectionDropdown";
    static components = { Dropdown, DropdownItem };

    static props = { section: Object };
}
