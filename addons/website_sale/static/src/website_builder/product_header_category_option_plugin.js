import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class ProductHeaderCategoryOptionPlugin extends Plugin {
    static id = "ProductHeaderCategoryOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dirt_marks: {
            id: "product-header",
            setDirtyOnMutation: (mutation, targetNode) =>
                mutation.type === "classList" && targetNode.id === "o_wsale_products_header"
                    ? targetNode
                    : null,
            save: (el) =>
                rpc("/shop/config/category", {
                    category_id: el.dataset.categoryId,
                    show_category_title: el.classList.contains("o_wsale_products_header_show_category_title"),
                    show_category_description: el.classList.contains("o_wsale_products_header_show_category_description"),
                    align_category_content: el.classList.contains("o_wsale_products_header_category_center_content"),
                }),
        },
    };
}

registry
    .category("website-plugins")
    .add(ProductHeaderCategoryOptionPlugin.id, ProductHeaderCategoryOptionPlugin);
