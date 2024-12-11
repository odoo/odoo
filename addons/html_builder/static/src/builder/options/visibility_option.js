import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class VisibilityOptionPlugin extends Plugin {
    static id = "VisibilityOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.VisibilityOption",
                selector: "section, .s_hr",
            },
        ],
    };
}
registry.category("website-plugins").add(VisibilityOptionPlugin.id, VisibilityOptionPlugin);
