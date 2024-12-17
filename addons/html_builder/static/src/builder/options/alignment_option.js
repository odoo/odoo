import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class AlignmentOptionPlugin extends Plugin {
    static id = "AlignmentOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.AlignmentOption",
                selector: ".s_share, .s_text_highlight, .s_social_media",
            },
        ],
    };
}
registry.category("website-plugins").add(AlignmentOptionPlugin.id, AlignmentOptionPlugin);
