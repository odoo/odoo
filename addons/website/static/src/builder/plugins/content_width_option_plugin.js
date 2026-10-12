import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";

export class ContentWidthOptionPlugin extends Plugin {
    static id = "contentWidthOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetContainerWidthAction,
        },
    };
}

export class SetContainerWidthAction extends ClassAction {
    static id = "setContainerWidth";
    apply({ isPreviewing, editingElement }) {
        super.apply(...arguments);
        editingElement.classList.toggle("o_container_preview", isPreviewing);
    }
}

registry.category("website-plugins").add(ContentWidthOptionPlugin.id, ContentWidthOptionPlugin);
