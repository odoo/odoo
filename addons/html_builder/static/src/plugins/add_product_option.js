import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class AddProductOption extends BaseOptionComponent {
    static id = "add_product_option";
    static template = "html_builder.AddProductOption";
    props = props({
        buttonApplyTo: t.string().optional(),
        productSelector: t.string().optional(),
        buttonLabel: t.string().optional(_t("Add Product")),
    });
}

registry.category("builder-options").add(AddProductOption.id, AddProductOption);
