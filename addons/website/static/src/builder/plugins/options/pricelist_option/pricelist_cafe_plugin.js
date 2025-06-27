import { VerticalAlignmentOption } from "@html_builder/plugins/vertical_alignment_option";
import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductOption } from "./add_product_option";

class PriceListCafePlugin extends Plugin {
    static id = "priceList";
    resources = {
        builder_options: [
            withSequence(BEGIN, {
                selector: ".s_pricelist_cafe",
                OptionComponent: AddProductOption,
                props: {
                    applyTo:
                        ":scope > :has(.s_pricelist_cafe_item):not(:has(.row > div .s_pricelist_cafe_item))",
                    productSelector: ".s_pricelist_cafe_item",
                },
            }),
            withSequence(BEGIN, {
                selector: ".s_pricelist_cafe",
                OptionComponent: VerticalAlignmentOption,
                applyTo: ".row:has(.s_pricelist_cafe_col)",
            }),
            withSequence(BEGIN, {
                selector: ".s_pricelist_cafe .row > div",
                OptionComponent: AddProductOption,
                props: {
                    applyTo: ":scope > :has(.s_pricelist_cafe_item)",
                    productSelector: ".s_pricelist_cafe_item",
                },
            }),
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.PriceListCafeDescriptionOption",
                selector: ".s_pricelist_cafe",
            }),
        ],
        dropzone_selector: {
            selector: ".s_pricelist_cafe_item",
            dropNear: ".s_pricelist_cafe_item",
        },
        is_movable_selector: { selector: ".s_pricelist_cafe_item", direction: "vertical" },
    };
}

registry.category("website-plugins").add(PriceListCafePlugin.id, PriceListCafePlugin);
