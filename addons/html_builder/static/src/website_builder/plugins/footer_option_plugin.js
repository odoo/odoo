import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";

class FooterOptionPlugin extends Plugin {
    static id = "footerOption";

    resources = {
        builder_options: [
            {
                template: "html_builder.FooterWidthOption",
                selector: "#wrapwrap > footer",
                applyTo:
                    ":is(:scope > #footer > section, .o_footer_copyright) > :is(.container, .container-fluid, .o_container_small)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(FooterOptionPlugin.id, FooterOptionPlugin);
