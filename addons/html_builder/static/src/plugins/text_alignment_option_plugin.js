import { TEXT_ALIGNMENT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BaseOptionComponent } from "@html_builder/core/utils";

class TextAlignmentOptionPlugin extends Plugin {
    static id = "textAlignmentOption";
    resources = {
        builder_options: [withSequence(TEXT_ALIGNMENT, TextAlignmentOption)],
    };
}

export class TextAlignmentOption extends BaseOptionComponent {
    static template = "html_builder.TextAlignmentOption";
    static selector = ".s_share, .s_text_highlight, .s_social_media";
}

registry.category("builder-plugins").add(TextAlignmentOptionPlugin.id, TextAlignmentOptionPlugin);
