import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { WIDTH } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";

class WidthOptionPlugin extends Plugin {
    static id = "widthOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_options: [withSequence(WIDTH, WidthOption)],
    };
}

export class WidthOption extends BaseOptionComponent {
    static template = "html_builder.WidthOption";
    static selector = ".s_alert, .s_blockquote, .s_text_highlight";
    static name = "widthOption";
}
registry.category("builder-plugins").add(WidthOptionPlugin.id, WidthOptionPlugin);
