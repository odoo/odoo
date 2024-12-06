import { Component } from "@odoo/owl";
import { useVisibleWithContent } from "../builder_helpers";

export class WeRow extends Component {
    static template = "html_builder.WeRow";
    static props = {
        label: String,
        tooltip: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        useVisibleWithContent("root", "content");
    }
}
