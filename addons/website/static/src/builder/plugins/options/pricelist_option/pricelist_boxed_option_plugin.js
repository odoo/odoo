import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseAddProductOption } from "@html_builder/plugins/add_product_option";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class PriceListBoxedDescriptionOption extends BaseOptionComponent {
    static template = "website.PriceListBoxedDescriptionOption";
    static selector = ".s_pricelist_boxed";
    static components = { BorderConfigurator };
}

export class AddProductPricelistBoxedOption extends BaseAddProductOption {
    static selector = ".s_pricelist_boxed";
    buttonApplyTo =
        ":scope > :has(.s_pricelist_boxed_item):not(:has(.row > div .s_pricelist_boxed_item))";
    productSelector = ".s_pricelist_boxed_item";
}

export class AddProductPricelistBoxedSectionOption extends BaseAddProductOption {
    static selector = ".s_pricelist_boxed_section";
    buttonApplyTo = ":scope > :has(.s_pricelist_boxed_item)";
    productSelector = ".s_pricelist_boxed_item";
}

class PriceListBoxedOptionPlugin extends Plugin {
    static id = "priceListBoxedOption";
    resources = {
        builder_options: [
            withSequence(BEGIN, AddProductPricelistBoxedOption),
            withSequence(BEGIN, AddProductPricelistBoxedSectionOption),
            withSequence(SNIPPET_SPECIFIC_END, PriceListBoxedDescriptionOption),
        ],
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
