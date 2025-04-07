import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";

    resources = {
        builder_options: [
            withSequence(1, {
                editableOnly: false,
                template: "website.headerTemplateOption",
                selector: "header",
                groups: ["website.group_website_designer"],
            }),
            withSequence(80, {
                editableOnly: false,
                template: "website.headerScrollEffectOption",
                selector: "#wrapwrap > header",
                groups: ["website.group_website_designer"],
            }),
            withSequence(100, {
                editableOnly: false,
                template: "website.headerElementOption",
                selector: "header",
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
