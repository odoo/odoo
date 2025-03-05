import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";

export class AddElementOption extends Component {
    static template = "html_builder.AddElementOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
}
