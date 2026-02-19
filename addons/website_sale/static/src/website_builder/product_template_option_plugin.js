import { Plugin } from "@html_editor/plugin";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { ProductTemplateOption } from "./product_template_option";

export class ProductTemplateOptionPlugin extends Plugin {
    static id = "productTemplateOptionPlugin";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, ProductTemplateOption),
        ],
        builder_actions: {},
        container_title: {
            selector: ProductTemplateOption.selector,
            getTitleExtraInfo: (el) => {
                const titleEl = el.querySelector(".o_wsale_product_details_content_section_title")?.querySelector("h1");
                return titleEl ? titleEl.textContent : "";
            },
            editableOnly: false,
        },
        patch_builder_options: [
            {
                target_name: 'ProductsRibbonOption',
                target_element: 'selector',
                method: 'add',
                value: ProductTemplateOption.selector,
            },
        ],
    };
}

registry.category("website-plugins")
        .add(ProductTemplateOptionPlugin.id, ProductTemplateOptionPlugin);
