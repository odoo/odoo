import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const ROUNDED_SIZE_CLASSES = [
    "rounded-0",
    "rounded-1",
    "rounded-2",
    "rounded-3",
    "rounded-4",
    "rounded-5",
    "rounded-circle",
    "rounded-pill",
];

export class BorderConfiguratorOptionPlugin extends Plugin {
    static id = "borderConfiguratorOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            SetBorderRadius,
        },
    };
}

export class SetBorderRadius extends ClassAction {
    static id = "setBorderRadius";
    apply({ editingElement }) {
        editingElement.classList.remove(...ROUNDED_SIZE_CLASSES);
        super.apply(...arguments);
    }
}

registry
    .category("builder-plugins")
    .add(BorderConfiguratorOptionPlugin.id, BorderConfiguratorOptionPlugin);
