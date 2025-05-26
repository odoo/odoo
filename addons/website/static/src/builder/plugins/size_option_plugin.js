import { after } from "@html_builder/utils/option_sequence";
import { BLOCK_ALIGN } from "@website/builder/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class SizeOptionPlugin extends Plugin {
    static id = "sizeOption";
    resources = {
        builder_options: [
            withSequence(after(BLOCK_ALIGN), {
                template: "html_builder.SizeOption",
                selector: ".s_alert",
            }),
        ],
    };
}
registry.category("website-plugins").add(SizeOptionPlugin.id, SizeOptionPlugin);
