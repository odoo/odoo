import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class PriceListBoxedOptionPlugin extends Plugin {
    static id = "priceListBoxedOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".s_pricelist_boxed_item",
            dropNear: ".s_pricelist_boxed_item",
        },
        is_movable_selectors: { selector: ".s_pricelist_boxed_item", direction: "vertical" },
        // Protect pricelist item, price, and description blocks from being
        // split/merged by the delete plugin.
        is_node_splittable_predicates: (node) => {
            if (
                isElement(node) &&
                node.matches(
                    ".s_pricelist_boxed_item, .s_pricelist_boxed_item_price, .s_pricelist_boxed_item_description"
                )
            ) {
                return false;
            }
        },
    };
}

export class PriceListBoxedDescriptionOption extends BaseOptionComponent {
    static id = "price_list_boxed_description_option";
    static template = "website.PriceListBoxedDescriptionOption";
    static components = { WebsiteBorderConfigurator };
}

registry.category("website-plugins").add(PriceListBoxedOptionPlugin.id, PriceListBoxedOptionPlugin);
registry
    .category("website-options")
    .add(PriceListBoxedDescriptionOption.id, PriceListBoxedDescriptionOption);
