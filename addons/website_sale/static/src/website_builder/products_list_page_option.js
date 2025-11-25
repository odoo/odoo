import { BaseOptionComponent } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { products_sort_mapping } from "@website_sale/website_builder/shared";

export class ProductsListPageOption extends BaseOptionComponent {
    static template = "website_sale.ProductsListPageOption";
    static selector = "#o_wsale_container";
    static title = _t("Products Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.products_sort_mapping = products_sort_mapping;
    }
}
