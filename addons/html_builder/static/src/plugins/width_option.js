import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class WidthOptionPlugin extends Plugin {
    static id = "WidthOption";
    resources = {
        builder_options: [
            withSequence(10, {
                template: "html_builder.WidthOption",
                selector: ".s_alert, .s_blockquote, .s_text_highlight",
            }),
        ],
    };
}
registry.category("website-plugins").add(WidthOptionPlugin.id, WidthOptionPlugin);
