import { BaseOptionComponent } from "@html_builder/core/utils";
import { products_sort_mapping } from "@website_sale/website_builder/shared";
import { ProductsDesignOverlayMixin } from "@website_sale/website_builder/products_design_overlay_mixin";

export class ProductsListPageOption extends ProductsDesignOverlayMixin(BaseOptionComponent) {
    static template = "website_sale.ProductsListPageOption";

    setup() {
        super.setup();
        this.products_sort_mapping = products_sort_mapping;
    }
}
