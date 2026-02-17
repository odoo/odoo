import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

export class ProductCatalogOptionPlugin extends Plugin {
    static id = "productCatalogOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_product_catalog_dish",
            dropNear: ".s_product_catalog_dish",
        },
        is_movable_selector: { selector: ".s_product_catalog_dish", direction: "vertical" },
        // Protect pricelist item, price, and description blocks from being
        // split/merged by the delete plugin.
        unsplittable_node_predicates: (node) =>
            isElement(node) &&
            node.matches(
                ".s_product_catalog_dish, .s_product_catalog_dish_price, .s_product_catalog_dish_description"
            ),
    };
}

registry.category("website-plugins").add(ProductCatalogOptionPlugin.id, ProductCatalogOptionPlugin);
