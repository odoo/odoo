import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductOption } from "./add_product_option";

class PriceListCafePlugin extends Plugin {
    static id = "priceList";
    resources = {
        builder_options: [
            withSequence(5, {
                selector: ".s_pricelist_cafe",
                OptionComponent: AddProductOption,
                props: {
                    applyTo:
                        ":scope > :has(.s_pricelist_cafe_item):not(:has(.row > div .s_pricelist_cafe_item))",
                    productSelector: ".s_pricelist_cafe_item",
                },
            }),
            withSequence(6, {
                selector: ".s_pricelist_cafe",
                template: "html_builder.VerticalAlignmentOption",
                applyTo: ".row:has(.s_pricelist_cafe_col)",
            }),
            withSequence(5, {
                selector: ".s_pricelist_cafe .row > div",
                OptionComponent: AddProductOption,
                props: {
                    applyTo: ":scope > :has(.s_pricelist_cafe_item)",
                    productSelector: ".s_pricelist_cafe_item",
                },
            }),
            withSequence(10, {
                template: "html_builder.PriceListCafeDescriptionOption",
                selector: ".s_pricelist_cafe",
            }),
        ],
        dropzone_selector: {
            selector: ".s_pricelist_cafe_item",
            dropNear: ".s_pricelist_cafe_item",
        },
    };
}

registry.category("website-plugins").add(PriceListCafePlugin.id, PriceListCafePlugin);
