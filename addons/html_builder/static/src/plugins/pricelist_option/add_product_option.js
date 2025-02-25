import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../../core/default_builder_components";

export class AddProductOption extends Component {
    static template = "html_builder.AddProductOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        applyTo: String,
        productSelector: String,
    };
}
