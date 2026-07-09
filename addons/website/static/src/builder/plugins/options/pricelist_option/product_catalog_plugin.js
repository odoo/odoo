import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ProductCatalogOptionPlugin extends Plugin {
    static id = "productCatalogOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_product_catalog_dish",
            dropNear: ".s_product_catalog_dish",
        },
        is_movable_selectors: { selector: ".s_product_catalog_dish", direction: "vertical" },
        region_properties: {
            // Protect pricelist item, price, and description blocks from being
            // split/merged by the delete plugin.
            is: ".s_product_catalog_dish, .s_product_catalog_dish_price, .s_product_catalog_dish_description",
            splittable: false,
        },
    };
}

registry.category("website-plugins").add(ProductCatalogOptionPlugin.id, ProductCatalogOptionPlugin);
