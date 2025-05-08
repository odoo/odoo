import { after } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BentoBorderOptionPlugin extends Plugin {
    static id = "BentoBorderOption";
    resources = {
        builder_options: [
            withSequence(after(WEBSITE_BACKGROUND_OPTIONS), {
                template: "html_builder.BentoBorderOption",
                selector: ".s_bento_banner section[data-name='Card'], .s_bento_block_card",
            }),
        ],
    };
}
registry.category("website-plugins").add(BentoBorderOptionPlugin.id, BentoBorderOptionPlugin);
