import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

export class PriceListCafePlugin extends Plugin {
    static id = "priceList";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_pricelist_cafe_item",
            dropNear: ".s_pricelist_cafe_item",
        },
        is_movable_selector: { selector: ".s_pricelist_cafe_item", direction: "vertical" },
        // Protect pricelist item, price, and description blocks from being
        // split/merged by the delete plugin.
        unsplittable_node_predicates: (node) =>
            isElement(node) &&
            node.matches(
                ".s_pricelist_cafe_item, .s_pricelist_cafe_item_price, .s_pricelist_cafe_item_description"
            ),
    };
}

registry.category("website-plugins").add(PriceListCafePlugin.id, PriceListCafePlugin);
