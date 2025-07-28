import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { FONT_AWESOME } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class FontAwesomeOption extends BaseOptionComponent {
    static template = "website.FontAwesomeOption";
    static selector = "span.fa, i.fa";
    static exclude = "[data-oe-xpath]";
    static components = { BorderConfigurator };
}

class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOptionPlugin";
    resources = {
        builder_options: [withSequence(FONT_AWESOME, FontAwesomeOption)],
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
