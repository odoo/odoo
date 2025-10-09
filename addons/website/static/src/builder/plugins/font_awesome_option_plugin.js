import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { FONT_AWESOME } from "@html_builder/utils/option_sequence";

class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOptionPlugin";
    resources = {
        builder_options: [
            withSequence(FONT_AWESOME, {
                template: "website.FontAwesomeOption",
                selector: "span.fa, i.fa",
                exclude: "[data-oe-xpath], .oe_login_form i.fa",
            }),
        ],
        builder_actions: {
            FaResizeAction,
        },
    };
}

export class FaResizeAction extends ClassAction {
    static id = "faResize";
    apply(context) {
        const { editingElement } = context;
        editingElement.classList.remove("fa-1x", "fa-lg");
        super.apply(context);
    }
}

registry.category("website-plugins").add(FontAwesomeOptionPlugin.id, FontAwesomeOptionPlugin);
