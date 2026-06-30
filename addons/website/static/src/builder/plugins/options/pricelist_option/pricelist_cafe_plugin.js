import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class PriceListCafePlugin extends Plugin {
    static id = "priceList";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_pricelist_cafe_item",
            dropNear: ".s_pricelist_cafe_item",
        },
        is_movable_selectors: { selector: ".s_pricelist_cafe_item", direction: "vertical" },
        region_properties: {
            // Protect pricelist item, price, and description blocks from being
            // split/merged by the delete plugin.
            is: ".s_pricelist_cafe_item, .s_pricelist_cafe_item_price, .s_pricelist_cafe_item_description",
            splittable: false,
        },
    };
}

registry.category("website-plugins").add(PriceListCafePlugin.id, PriceListCafePlugin);
