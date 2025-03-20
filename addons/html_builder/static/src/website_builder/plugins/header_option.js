import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";

    resources = {
        builder_options: [
            withSequence(100, {
                editableOnly: false,
                template: "website.headerElementOption",
                selector: "header",
            }),
        ],
    };
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
