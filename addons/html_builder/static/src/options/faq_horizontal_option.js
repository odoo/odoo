import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class FaqHorizontalOptionPlugin extends Plugin {
    static id = "FaqHorizontalOption";
    static dependencies = ["clone"];
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.FaqHorizontalOption",
                selector: ".s_faq_horizontal",
            }),
        ],
    };
}
registry.category("website-plugins").add(FaqHorizontalOptionPlugin.id, FaqHorizontalOptionPlugin);
