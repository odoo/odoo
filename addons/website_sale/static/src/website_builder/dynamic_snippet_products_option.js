import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class DynamicSnippetProductsOption extends BaseOptionComponent {
    static id = "dynamic_snippet_products_option";
    static template = "website_sale.DynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetProductsOption"];

    setup() {
        super.setup();
        const { fetchCategories, getModelNameFilter } =
            this.dependencies.dynamicSnippetProductsOption;
        this.modelNameFilter = getModelNameFilter();
        const contextualFilterDomain = getContextualFilterDomain(this.env.editor.editable);
        this.dynamicOptionParams = useDynamicSnippetOption(
            this.modelNameFilter,
            contextualFilterDomain
        );
        this.state = proxy({
            categories: [],
        });
        onWillStart(async () => {
            this.state.categories.push(...(await fetchCategories()));
        });
    }
}

registry.category("website-options").add(DynamicSnippetProductsOption.id, DynamicSnippetProductsOption);

export function getContextualFilterDomain(editable) {
    const productTemplateId = parseInt(editable.querySelector(
        ".js_product [data-product-template-id]"
    )?.dataset?.productTemplateId);
    return productTemplateId ? [] : [["product_cross_selling", "=", false]];
}
