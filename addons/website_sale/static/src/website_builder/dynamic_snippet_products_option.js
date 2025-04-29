import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { DynamicSnippetCarouselOption } from "@website/builder/plugins/options/dynamic_snippet_carousel_option";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { onWillStart, useState } from "@odoo/owl";

export class DynamicSnippetProductsOption extends BaseOptionComponent {
    static template = "website_sale.DynamicSnippetProductsOption";
    static props = {
        ...DynamicSnippetCarouselOption.props,
        fetchCategories: Function,
    };
    setup() {
        super.setup();
        const contextualFilterDomain = getContextualFilterDomain(this.env.editor.editable);
        this.dynamicOptionParams = useDynamicSnippetOption(
            this.props.modelNameFilter,
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
            this.state.categories.push(...(await this.props.fetchCategories()));
        });
    }
}

export function getContextualFilterDomain(editable) {
    const productTemplateId = editable.querySelector("input.product_template_id");
    const hasProductTemplateId = productTemplateId?.value;
    return hasProductTemplateId ? [] : [["product_cross_selling", "=", false]];
}
