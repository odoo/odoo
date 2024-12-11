import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";

// todo: this is a naive implemenation. We should look at the current
// implementations of backgrounds options for all targets instead of just
// focusing on sections.
class SectionBackgroundOptionPlugin extends Plugin {
    static id = "SectionBackgroundOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.SectionBackgroundOption",
                selector: "section",
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(SectionBackgroundOptionPlugin.id, SectionBackgroundOptionPlugin);
