import { DynamicSnippetCarouselOption } from "@html_builder/plugins/dynamic_snippet_carousel_option";
import { onWillStart, useState } from "@odoo/owl";

export class DynamicSnippetProductsOption extends DynamicSnippetCarouselOption {
    static template = "website_sale.DynamicSnippetProductsOption";
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
