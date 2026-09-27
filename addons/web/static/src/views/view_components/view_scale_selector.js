import { Component, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export const viewScaleSelectorProps = {
    scales: t.object(),
    currentScale: t.string(),
    isWeekendVisible: t.boolean().optional(),
    setScale: t.function(),
    toggleWeekendVisibility: t.function().optional(),
    dropdownClass: t.string().optional(),
};

export class ViewScaleSelector extends Component {
    static components = {
        Dropdown,
        DropdownItem,
    };
    static template = "web.ViewScaleSelector";
    props = useProps(viewScaleSelectorProps);
    get scales() {
        return Object.entries(this.props.scales).map(([key, value]) => ({ key, ...value }));
    }
    get isWeekendButtonDisabled() {
        return this.props.currentScale === "day";
    }
}
