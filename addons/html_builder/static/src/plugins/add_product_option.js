import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class AddProductOption extends BaseOptionComponent {
    static id = "add_product_option";
    static template = "html_builder.AddProductOption";
    static props = {
        buttonApplyTo: { type: String, optional: true },
        productSelector: { type: String, optional: true },
        buttonLabel: { type: String, optional: true },
    };
    static defaultProps = {
        buttonLabel: _t("Add Product"),
    };
}

registry.category("builder-options").add(AddProductOption.id, AddProductOption);
