import { BaseOptionComponent } from "@html_builder/core/utils";

export class AddProductOption extends BaseOptionComponent {
    static template = "html_builder.AddProductOption";
    static props = {
        applyTo: String,
        productSelector: String,
    };
}
