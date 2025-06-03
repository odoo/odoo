import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Snippets often uses an empty div with .o_we_shape or .o_we_bg_filter to be a
 * target for some scss rules, or some js behaviour. This is a problem for the
 * website builder, because these divs are present in the DOM and therefore
 * editable. This interaction simply tag them as not editable to avoid the user
 * accidentally editing them.
 */
class DisableMetaDataElements extends Interaction {
    static selector = ".o_we_bg_filter,.o_we_shape";
    dynamicContent = {
        _root: {
            "t-att-contenteditable": () => "false",
        },
    };
}

registry.category("public.interactions.edit").add("website.disable_metadata", {
    Interaction: DisableMetaDataElements,
});
