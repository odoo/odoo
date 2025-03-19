import { Component } from "@odoo/owl";
import { useBuilderComponents } from "@html_builder/core/utils";

export class AddProductOption extends Component {
    static template = "html_builder.AddProductOption";
    static props = {
        applyTo: String,
        productSelector: String,
    };
    setup() {
        useBuilderComponents();
    }
}
