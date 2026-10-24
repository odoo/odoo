import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { fetchProductSearchData } from "../snippets/s_product_search/product_search_utils";

export class ProductSearchOption extends BaseOptionComponent {
    static id = "product_search_option";
    static template = "website_sale.ProductSearchOption";

    setup() {
        super.setup();
        this.state = useDomState(async () => {
            const { attributes, categories, tags, ribbons } = await fetchProductSearchData();
            return { attributes, categories, tags, ribbons };
        });
    }
}

registry.category("website-options").add(ProductSearchOption.id, ProductSearchOption);

export class ProductSearchAttributeFilterOption extends BaseOptionComponent {
    static id = "product_search_attribute_filter_option";
    static template = "website_sale.ProductSearchAttributeFilterOption";

    setup() {
        super.setup();
        this.state = useDomState(async () => {
            const { attributes } = await fetchProductSearchData();
            return { attributes };
        });
    }
}

registry
    .category("website-options")
    .add(ProductSearchAttributeFilterOption.id, ProductSearchAttributeFilterOption);
