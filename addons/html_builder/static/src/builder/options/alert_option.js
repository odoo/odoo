import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class AlertOptionPlugin extends Plugin {
    static id = "AlertOption";
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.AlertOption",
                selector: ".s_alert",
            }),
        ],
    };
}
registry.category("website-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
