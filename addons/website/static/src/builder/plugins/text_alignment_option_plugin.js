import { TEXT_ALIGNMENT } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class TextAlignmentOptionPlugin extends Plugin {
    static id = "textAlignmentOption";
    resources = {
        builder_options: [
            withSequence(TEXT_ALIGNMENT, {
                template: "website.TextAlignmentOption",
                selector: ".s_share, .s_text_highlight, .s_social_media",
            }),
        ],
    };
}

registry.category("website-plugins").add(TextAlignmentOptionPlugin.id, TextAlignmentOptionPlugin);
