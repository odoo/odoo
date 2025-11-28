import { BaseOptionComponent } from "@html_builder/core/utils";
import { products_sort_mapping } from "@website_sale/website_builder/shared";
import { registry } from "@web/core/registry";

export class ProductsListPageOption extends BaseOptionComponent {
    static id = "products_list_page_option";
    static template = "website_sale.ProductsListPageOption";

    setup() {
        super.setup();
        this.products_sort_mapping = products_sort_mapping;
    }
}

registry.category("builder-options").add(ProductsListPageOption.id, ProductsListPageOption);
