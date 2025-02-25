import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ContentWidthOptionPlugin extends Plugin {
    static id = "contentWidthOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.ContentWidthOption",
                selector: "section, .s_carousel .carousel-item, .s_carousel_intro_item",
                exclude: "[data-snippet] :not(.oe_structure) > [data-snippet]",
                // TODO  add target and remove applyTo in the template of ContentWidthOption ?
                // target: "> .container, > .container-fluid, > .o_container_small",
            },
        ],
    };
}
registry.category("website-plugins").add(ContentWidthOptionPlugin.id, ContentWidthOptionPlugin);
