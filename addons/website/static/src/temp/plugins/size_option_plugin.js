import { after } from "@html_builder/utils/option_sequence";
import { WIDTH } from "@website/website_builder/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class SizeOptionPlugin extends Plugin {
    static id = "sizeOption";
    resources = {
        builder_options: [
            withSequence(after(WIDTH), {
                template: "html_builder.SizeOption",
                selector: ".s_alert",
            }),
        ],
    };
}
registry.category("website-plugins").add(SizeOptionPlugin.id, SizeOptionPlugin);
