import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseAddProductOption } from "@html_builder/plugins/add_product_option";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BaseVerticalAlignmentOption } from "@html_builder/plugins/base_vertical_alignment_option";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class PriceListCafeDescriptionOption extends BaseOptionComponent {
    static template = "website.PriceListCafeDescriptionOption";
    static selector = ".s_pricelist_cafe";
    static components = { BorderConfigurator };
}

export class PricelistCafeVerticalAlignmentOption extends BaseVerticalAlignmentOption {
    static selector = ".s_pricelist_cafe";
    static applyTo = ".row:has(.s_pricelist_cafe_col)";
    level = 0;
}

export class AddProductPricelistCafeOption extends BaseAddProductOption {
    static selector = ".s_pricelist_cafe";
    buttonApplyTo =
        ":scope > :has(.s_pricelist_cafe_item):not(:has(.row > div .s_pricelist_cafe_item))";
    productSelector = ".s_pricelist_cafe_item";
}

export class AddProductPricelistCafeRowOption extends BaseAddProductOption {
    static selector = ".s_pricelist_cafe .row > div";
    buttonApplyTo = ":scope > :has(.s_pricelist_cafe_item)";
    productSelector = ".s_pricelist_cafe_item";
}

class PriceListCafePlugin extends Plugin {
    static id = "priceList";
    resources = {
        builder_options: [
            withSequence(BEGIN, AddProductPricelistCafeOption),
            withSequence(BEGIN, PricelistCafeVerticalAlignmentOption),
            withSequence(BEGIN, AddProductPricelistCafeRowOption),
            withSequence(SNIPPET_SPECIFIC_END, PriceListCafeDescriptionOption),
        ],
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
