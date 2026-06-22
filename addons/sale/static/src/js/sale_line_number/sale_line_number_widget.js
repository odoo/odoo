/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class LineNumberWidget extends Component {
    static template = "sale.LineNumber";
    static props = { ...standardWidgetProps };
}

export const lineNumber = {
    component: LineNumberWidget,
};

registry.category("view_widgets").add("line_number", lineNumber);
