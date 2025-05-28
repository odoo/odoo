import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { WIDTH } from "@website/builder/option_sequence";

class WidthOptionPlugin extends Plugin {
    static id = "widthOption";
    resources = {
        builder_options: [
            withSequence(WIDTH, {
                template: "website.WidthOption",
                selector: ".s_alert, .s_blockquote, .s_text_highlight",
            }),
        ],
    };
}
registry.category("website-plugins").add(WidthOptionPlugin.id, WidthOptionPlugin);
