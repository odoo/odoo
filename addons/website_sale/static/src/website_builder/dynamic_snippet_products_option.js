import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { onWillStart, useState } from "@odoo/owl";

export class DynamicSnippetProductsOption extends BaseOptionComponent {
    static template = "website_sale.DynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetProductsOption"];
    static selector = ".s_dynamic_snippet_products";
    setup() {
        super.setup();
        const { fetchCategories, getModelNameFilter } = this.dependencies.dynamicSnippetProductsOption;
        const contextualFilterDomain = getContextualFilterDomain(this.env.editor.editable);
        this.dynamicOptionParams = useDynamicSnippetOption(
            getModelNameFilter(),
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

export function getContextualFilterDomain(editable) {
    const productTemplateId = editable.querySelector("input.product_template_id");
    const hasProductTemplateId = productTemplateId?.value;
    return hasProductTemplateId ? [] : [["product_cross_selling", "=", false]];
}
