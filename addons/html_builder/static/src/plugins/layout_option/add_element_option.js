import { useBuilderComponents } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";

export class AddElementOption extends Component {
    static template = "html_builder.AddElementOption";
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        level: 0,
    };

    setup() {
        useBuilderComponents();
    }
}
