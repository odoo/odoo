import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class accordionOptionPlugin extends Plugin {
    static id = "accordionOptionPlugin";
    static dependencies = ["clone"];
    resources = {
        builder_options: [
            {
                template: "html_builder.AccordionOption",
                selector: ".s_accordion",
            },
            {
                template: "html_builder.AccordionItemOption",
                selector: ".s_accordion .accordion-item",
            },
        ],
    };
}

registry.category("website-plugins").add(accordionOptionPlugin.id, accordionOptionPlugin);
