import { Component } from "@odoo/owl";

export class ToolboxRow extends Component {
    static template = "html_builder.ToolboxRow";
    static props = {
        label: String,
        slots: { type: Object, optional: true },
    };
}
