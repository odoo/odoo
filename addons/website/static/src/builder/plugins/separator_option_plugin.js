import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class SeparatorOptionPlugin extends Plugin {
    static id = "separatorOption";
    resources = {
        builder_options: [
            {
                template: "website.SeparatorOption",
                selector: ".s_hr",
                applyTo: "hr",
            },
        ],
        dropzone_selector: {
            selector: ".s_hr",
            dropNear: "p, h1, h2, h3, blockquote, .s_hr",
        },
        so_content_addition_selector: [".s_hr"],
    };
}
registry.category("website-plugins").add(SeparatorOptionPlugin.id, SeparatorOptionPlugin);
