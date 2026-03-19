import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class IconOptionPlugin extends Plugin {
    static id = "iconOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            IconResizeAction,
        },
    };
}

export class IconResizeAction extends ClassAction {
    static id = "iconResize";
    apply(context) {
        const { editingElement } = context;
        editingElement.classList.remove("oi-1x", "oi-lg");
        super.apply(context);
    }
}

registry.category("website-plugins").add(IconOptionPlugin.id, IconOptionPlugin);
