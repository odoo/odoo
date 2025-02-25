import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class SizeOptionPlugin extends Plugin {
    static id = "sizeOption";
    resources = {
        builder_options: [
            withSequence(20, {
                template: "html_builder.SizeOption",
                selector: ".s_alert",
            }),
        ],
    };
}
registry.category("website-plugins").add(SizeOptionPlugin.id, SizeOptionPlugin);
