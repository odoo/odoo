import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class PriceListBoxedOptionPlugin extends Plugin {
    static id = "priceListBoxedOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_pricelist_boxed_item",
            dropNear: ".s_pricelist_boxed_item",
        },
        is_movable_selectors: { selector: ".s_pricelist_boxed_item", direction: "vertical" },
        region_properties: {
            // Protect pricelist item, price, and description blocks from being
            // split/merged by the delete plugin.
            is: ".s_pricelist_boxed_item, .s_pricelist_boxed_item_price, .s_pricelist_boxed_item_description",
            splittable: false,
        },
    };
}

registry.category("website-plugins").add(PriceListBoxedOptionPlugin.id, PriceListBoxedOptionPlugin);
