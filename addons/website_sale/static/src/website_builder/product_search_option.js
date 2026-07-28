import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useOperation } from "@html_builder/core/operation_plugin";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { fetchProductSearchData, renderAttributeFilter } from "../snippets/s_product_search/product_search_utils";

export class ProductSearchOption extends BaseOptionComponent {
    static id = "product_search_option";
    static template = "website_sale.ProductSearchOption";
    static dependencies = ["builderOptions"];

    setup() {
        super.setup();
        this.callOperation = useOperation();
        this.state = useDomState(async () => {
            const { attributes, categories, tags, ribbons } = await fetchProductSearchData();
            return { attributes, categories, tags, ribbons };
        });
    }

    addAttributeFilter() {
        const { attributes } = this.state;
        this.callOperation(() => {
            const el = this.env.getEditingElement();
            const attributesEl = el.querySelector(".s_product_search_attributes");
            const filterEl = document.createElement("div");
            filterEl.className = "s_product_search_attribute_filter";
            if (attributes.length) {
                filterEl.dataset.attributeId = attributes[0].id;
            }
            attributesEl.appendChild(filterEl);
            renderAttributeFilter(filterEl, attributes);
            this.dependencies.builderOptions.setNextTarget(filterEl);
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
