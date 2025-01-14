import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class PriceListCafeOptionPlugin extends Plugin {
    static id = "PriceListCafeOption";
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.PriceListCafeOption",
                selector: ".s_pricelist_cafe",
            }),
            withSequence(5, {
                template: "html_builder.PriceListCafeRowDivOption",
                selector: ".s_pricelist_cafe .row > div",
            }),
            withSequence(10, {
                template: "html_builder.PriceListCafeDescriptionOption",
                selector: ".s_pricelist_cafe",
            }),
        ],
        builder_actions: this.getActions(),
    };
}

registry.category("website-plugins").add(PriceListCafeOptionPlugin.id, PriceListCafeOptionPlugin);
