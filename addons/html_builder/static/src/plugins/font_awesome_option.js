import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { classAction } from "../core/plugins/core_builder_action_plugin";

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
