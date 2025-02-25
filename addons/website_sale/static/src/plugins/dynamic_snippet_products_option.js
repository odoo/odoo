import { onWillStart, useState } from "@odoo/owl";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetCarouselOption } from "@html_builder/plugins/dynamic_snippet_carousel_option_plugin";

export class DynamicSnippetProductsOption extends DynamicSnippetCarouselOption {
    static template = "website_sale.DynamicSnippetProductsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        ...DynamicSnippetCarouselOption.props,
        fetchCategories: Function,
    };
    setup() {
        super.setup();
        this.modelNameFilter = "product.product";
        this.saleState = useState({
            categories: [],
        });
        onWillStart(async () => {
            this.saleState.categories.push(...(await this.props.fetchCategories()));
        });
    }
}
