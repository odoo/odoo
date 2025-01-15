import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductButton } from "./pricelist_option";

class PriceListBoxedOptionPlugin extends Plugin {
    static id = "PriceListBoxedOption";
    resources = {
        builder_options: [
            withSequence(5, {
                selector: ".s_pricelist_boxed",
                OptionComponent: AddProductButton,
                props: {
                    applyTo:
                        ":scope > :has(.s_pricelist_boxed_item):not(:has(.row > div .s_pricelist_boxed_item))",
                    productSelector: ".s_pricelist_boxed_item",
                },
            }),
            withSequence(5, {
                selector: ".s_pricelist_boxed_section",
                OptionComponent: AddProductButton,
                props: {
                    applyTo: ":scope > :has(.s_pricelist_boxed_item)",
                    productSelector: ".s_pricelist_boxed_item",
                },
            }),
            withSequence(10, {
                template: "html_builder.PriceListBoxedDescriptionOption",
                selector: ".s_pricelist_boxed",
            }),
        ],
        dropzone_selector: {
            selector: ".s_pricelist_boxed_item",
            dropNear: ".s_pricelist_boxed_item",
        },
    };
}

registry.category("website-plugins").add(PriceListBoxedOptionPlugin.id, PriceListBoxedOptionPlugin);
