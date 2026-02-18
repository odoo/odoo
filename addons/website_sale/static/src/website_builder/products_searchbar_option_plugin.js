import { products_sort_mapping } from "@website_sale/website_builder/shared";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ProductsSearchbarOptionPlugin extends Plugin {
    static id = "productsSearchbarOption";

    resources = {
        // 'name asc' is already part of the general sorting methods of this
        // snippet.
        searchbar_option_order_by_items: products_sort_mapping
            .filter((sort) => sort.query !== "name asc")
            .map((query_and_label) => ({
                label: query_and_label.label,
                orderBy: query_and_label.query,
                dependency: "search_products_opt",
            })),
    };
}

registry
    .category("website-plugins")
    .add(ProductsSearchbarOptionPlugin.id, ProductsSearchbarOptionPlugin);
