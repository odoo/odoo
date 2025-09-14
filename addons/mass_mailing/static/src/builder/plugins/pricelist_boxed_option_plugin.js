import { AddProductOption } from "@html_builder/plugins/add_product_option";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BEGIN } from "@html_builder/utils/option_sequence";
import { registry } from "@web/core/registry";

export class PricelistBoxedOptionPlugin extends Plugin {
    static id = "mass_mailing.PricelistBoxedOptionPlugin";
    resources = {
        builder_options: [
            withSequence(BEGIN, {
                selector: ".s_pricelist_boxed_section:has(> .container)",
                OptionComponent: AddProductOption,
                props: {
                    productSelector: ".container",
                },
            }),
        ],
    };
}

registry
    .category("mass_mailing-plugins")
    .add(PricelistBoxedOptionPlugin.id, PricelistBoxedOptionPlugin);
