// @ts-check

/** @module @web/views/view_components/view_scale_selector - Dropdown for switching between time scales (day/week/month/year) in calendar and gantt views */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
/** Dropdown for switching between time scales (day/week/month/year) in calendar and gantt views. */
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
        return Object.entries(this.props.scales).map(([key, value]) => ({
            key,
            ...value,
        }));
    }
}
