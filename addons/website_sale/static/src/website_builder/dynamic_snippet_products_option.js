import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { onWillStart, useState } from "@odoo/owl";
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
        this.state = useState({
            categories: [],
        });
        this.domState = useDomState((el) => ({
            isAlternative: el.classList.contains("o_wsale_alternative_products"),
        }));
        this.dynamicOptionParams.showFilterOption = () =>
            Object.values(this.dynamicOptionParams.dynamicFilters).length > 1 &&
            !this.domState.isAlternative;
        onWillStart(async () => {
            this.state.categories.push(...(await fetchCategories()));
        });
    }
}

registry.category("builder-options").add(DynamicSnippetProductsOption.id, DynamicSnippetProductsOption);

export function getContextualFilterDomain(editable) {
    const productTemplateId = parseInt(editable.querySelector(
        ".js_product [data-product-template-id]"
    )?.dataset?.productTemplateId);
    return productTemplateId ? [] : [["product_cross_selling", "=", false]];
}
