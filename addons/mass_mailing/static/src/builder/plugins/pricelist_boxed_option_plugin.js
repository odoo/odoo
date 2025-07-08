import { Plugin } from "@html_editor/plugin";
import { AddProductOption } from "../options/add_product_option";
import { withSequence } from "@html_editor/utils/resource";
import { BEGIN } from "@html_builder/utils/option_sequence";
import { registry } from "@web/core/registry";

export class PricelistBoxedOptionPlugin extends Plugin {
    static id = "mass_mailing.PricelistBoxedOptionPlugin";
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
        ],
    };
}

registry
    .category("mass_mailing-plugins")
    .add(PricelistBoxedOptionPlugin.id, PricelistBoxedOptionPlugin);
