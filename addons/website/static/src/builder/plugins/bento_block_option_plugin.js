import { after } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BentoBlockOptionPlugin extends Plugin {
    static id = "bentoBlockOption";
    resources = {
        builder_options: [
            withSequence(after(WEBSITE_BACKGROUND_OPTIONS), {
                template: "html_builder.BentoBlockOption",
                selector: ".s_bento_block_card",
            }),
        ],
    };
}
registry.category("website-plugins").add(BentoBlockOptionPlugin.id, BentoBlockOptionPlugin);
