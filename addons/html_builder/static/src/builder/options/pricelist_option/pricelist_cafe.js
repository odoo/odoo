import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductButton } from "./pricelist_option";

class PriceListCafeOptionPlugin extends Plugin {
    static id = "PriceListCafeOption";
    resources = {
        builder_options: [
            withSequence(5, {
                selector: ".s_pricelist_cafe",
                OptionComponent: AddProductButton,
                props: {
                    applyTo:
                        ":scope > :has(.s_pricelist_cafe_item):not(:has(.row > div .s_pricelist_cafe_item))",
                    productSelector: ".s_pricelist_cafe_item",
                },
            }),
            withSequence(5, {
                selector: ".s_pricelist_cafe .row > div",
                OptionComponent: AddProductButton,
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
    };
}

registry.category("website-plugins").add(PriceListCafeOptionPlugin.id, PriceListCafeOptionPlugin);
