import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ViewScaleSelector extends Component {
    static components = {
        Dropdown,
        DropdownItem,
    };
    static template = "web.ViewScaleSelector";
    static props = {
        scales: { type: Object },
        currentScale: { type: String },
        isWeekendVisible: { type: Boolean, optional: true },
        setScale: { type: Function },
        toggleWeekendVisibility: { type: Function, optional: true },
        dropdownClass: { type: String, optional: true },
    };
    get scales() {
        return Object.entries(this.props.scales).map(([key, value]) => ({ key, ...value }));
    }
}
