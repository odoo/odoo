import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { classAction } from "@html_builder/core/core_builder_action_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { FONT_AWESOME } from "@html_builder/utils/option_sequence";

class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOptionPlugin";
    resources = {
        builder_options: [
            withSequence(FONT_AWESOME, {
                template: "html_builder.FontAwesomeOption",
                selector: "span.fa, i.fa",
                exclude: "[data-oe-xpath]",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            faResize: {
                ...classAction,
                apply: function ({ editingElement }) {
                    editingElement.classList.remove("fa-1x", "fa-lg");
                    classAction.apply(...arguments);
                },
            },
        };
    }
}
registry.category("website-plugins").add(FontAwesomeOptionPlugin.id, FontAwesomeOptionPlugin);
