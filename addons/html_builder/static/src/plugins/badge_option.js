import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class BadgeOptionPlugin extends Plugin {
    static id = "BadgeOption";
    resources = {
        builder_options: [
            withSequence(10, {
                template: "html_builder.BadgeOption",
                selector: ".s_badge",
            }),
        ],
    };
}
registry.category("website-plugins").add(BadgeOptionPlugin.id, BadgeOptionPlugin);
