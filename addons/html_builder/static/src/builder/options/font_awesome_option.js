import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class FontAwesomeOptionPlugin extends Plugin {
    static id = "FontAwesomeOptionPlugin";
    resources = {
        builder_options: [
            {
                template: "html_builder.FontAwesomeOption",
                selector: "span.fa, i.fa",
                exclude: "[data-oe-xpath]",
            },
        ],
    };
}
registry.category("website-plugins").add(FontAwesomeOptionPlugin.id, FontAwesomeOptionPlugin);
