import { Component } from "@odoo/owl";

export class WeRow extends Component {
    static template = "html_builder.WeRow";
    static props = {
        label: String,
        slots: { type: Object, optional: true },
    };
}
