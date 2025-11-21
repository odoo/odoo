import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ProductTemplateOptionPlugin extends Plugin {
    static id = "productTemplateOptionPlugin";
    resources = {
        builder_actions: {},
        builder_options_render_context: {
            productTemplateOptionSelector: ".o_wsale_product_page:has(.variant_attribute)",
        },
    };
}

registry
    .category("website-plugins")
    .add(ProductTemplateOptionPlugin.id, ProductTemplateOptionPlugin);
