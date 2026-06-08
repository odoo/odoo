import { Component, props, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ReportViewMeasures extends Component {
    static template = "web.ReportViewMeasures";
    static components = {
        Dropdown,
        DropdownItem,
    };
    props = props({
        measures: t.any(),
        activeMeasures: t.array().optional(),
        multiSelect: t.boolean().optional(true),
        onMeasureSelected: t.function().optional(),
    });
}
