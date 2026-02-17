import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

export class PriceListBoxedOptionPlugin extends Plugin {
    static id = "priceListBoxedOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_pricelist_boxed_item",
            dropNear: ".s_pricelist_boxed_item",
        },
        is_movable_selector: { selector: ".s_pricelist_boxed_item", direction: "vertical" },
        // Protect pricelist item, price, and description blocks from being
        // split/merged by the delete plugin.
        unsplittable_node_predicates: (node) =>
            isElement(node) &&
            node.matches(
                ".s_pricelist_boxed_item, .s_pricelist_boxed_item_price, .s_pricelist_boxed_item_description"
            ),
    };
}

registry.category("website-plugins").add(PriceListBoxedOptionPlugin.id, PriceListBoxedOptionPlugin);
