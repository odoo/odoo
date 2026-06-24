import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";

export class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
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
