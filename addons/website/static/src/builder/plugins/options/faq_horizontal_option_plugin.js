import { BEGIN } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class FaqHorizontalOptionPlugin extends Plugin {
    static id = "faqHorizontalOption";
    static dependencies = ["clone"];
    resources = {
        builder_options: [
            withSequence(BEGIN, {
                template: "website.FaqHorizontalOption",
                selector: ".s_faq_horizontal",
            }),
        ],
    };
}
registry.category("website-plugins").add(FaqHorizontalOptionPlugin.id, FaqHorizontalOptionPlugin);
