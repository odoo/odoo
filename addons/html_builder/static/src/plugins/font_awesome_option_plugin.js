import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOption";
    /** @type {import("plugins").BuilderResources} */
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
        // In website, remove default FA size classes as sizing is handled by
        // Bootstrap classes.
        if (editingElement.closest("#wrapwrap")) {
            editingElement.classList.remove("fa-1x", "fa-lg");
        }
        super.apply(context);
    }
}

registry.category("builder-plugins").add(FontAwesomeOptionPlugin.id, FontAwesomeOptionPlugin);
