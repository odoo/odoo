import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductOption } from "./add_product_option";

class PriceListBoxedOptionPlugin extends Plugin {
    static id = "priceListBoxedOption";
    resources = {
        builder_options: [
            withSequence(BEGIN, {
                selector: ".s_pricelist_boxed",
                OptionComponent: AddProductOption,
                props: {
                    applyTo:
                        ":scope > :has(.s_pricelist_boxed_item):not(:has(.row > div .s_pricelist_boxed_item))",
                    productSelector: ".s_pricelist_boxed_item",
                },
            }),
            withSequence(BEGIN, {
                selector: ".s_pricelist_boxed_section",
                OptionComponent: AddProductOption,
                props: {
                    applyTo: ":scope > :has(.s_pricelist_boxed_item)",
                    productSelector: ".s_pricelist_boxed_item",
                },
            }),
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.PriceListBoxedDescriptionOption",
                selector: ".s_pricelist_boxed",
            }),
        ],
        dropzone_selector: {
            selector: ".s_pricelist_boxed_item",
            dropNear: ".s_pricelist_boxed_item",
        },
        is_movable_selector: { selector: ".s_pricelist_boxed_item", direction: "vertical" },
    };
}

registry.category("website-plugins").add(PriceListBoxedOptionPlugin.id, PriceListBoxedOptionPlugin);
