import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class TextAlignmentOptionPlugin extends Plugin {
    static id = "textAlignmentOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.TextAlignmentOption",
                selector: ".s_share, .s_text_highlight, .s_social_media",
            },
        ],
    };
}

registry.category("website-plugins").add(TextAlignmentOptionPlugin.id, TextAlignmentOptionPlugin);
