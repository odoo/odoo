import { BaseOptionComponent } from "@html_builder/core/utils";
import { products_sort_mapping } from "@website_sale/website_builder/shared";

export class ProductsListPageOption extends BaseOptionComponent {
    static template = "website_sale.ProductsListPageOption";
<<<<<<< 189f0506f09249c5a7c2f7b7a5b02d9bd996014d
||||||| a5c2f140db215765d628c9aa730bf13bf9cd2e6e
    static selector = "#o_wsale_container";
    static applyTo = "#o_wsale_container";
    static title = _t("Products Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
=======
    static selector = "#o_wsale_container";
    static title = _t("Products Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
>>>>>>> 71ee7df12f1e181720cd9810c3fba7ea88fd9206

    setup() {
        super.setup();
        this.products_sort_mapping = products_sort_mapping;
    }
}
