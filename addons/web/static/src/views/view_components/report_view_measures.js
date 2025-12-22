import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ReportViewMeasures extends Component {
    static template = "web.ReportViewMeasures";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        measures: true,
        activeMeasures: { type: Array, optional: true },
        onMeasureSelected: { type: Function, optional: true },
    };
}
