import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class AddProductOption extends BaseOptionComponent {
    static id = "add_product_option";
    static template = "html_builder.AddProductOption";
    static props = {
        buttonApplyTo: { type: String, optional: true },
        productSelector: { type: String, optional: true },
    };
}

registry.category("builder-options").add(AddProductOption.id, AddProductOption);
