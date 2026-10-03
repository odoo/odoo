import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useProps, t } from "@odoo/owl";

export class ProductsDesignPanel extends BaseOptionComponent {
    static template = "website_sale.ProductsDesignPanel";
    static components = {
        ...BaseOptionComponent.components,
    };
    props = useProps({
        label: t.string().optional("Design"),
        recordName: t.string().optional(),
        showLists: t.boolean().optional(true),
        showSecondaryImage: t.boolean().optional(false),
        openByDefault: t.boolean().optional(false),
    });
}
