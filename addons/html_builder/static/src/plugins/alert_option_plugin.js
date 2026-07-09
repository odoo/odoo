import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

export class AlertOptionPlugin extends Plugin {
    static id = "alertOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            AlertIconAction,
        },
        so_content_addition_selectors: [".s_alert"],
    };
}

export class AlertIconAction extends BuilderAction {
    static id = "alertIcon";
    apply({ editingElement, params: { mainParam: className } }) {
        const icon = editingElement.querySelector(".s_alert_icon");
        if (!icon) {
            return;
        }
        icon.dataset.icon = className;
    }
    clean({ editingElement, params: { mainParam: className } }) {
        const icon = editingElement.querySelector(".s_alert_icon");
        if (!icon) {
            return;
        }
    }
    isApplied({ editingElement, params: { mainParam: className } }) {
        const iconEl = editingElement.querySelector(".s_alert_icon");
        if (!iconEl) {
            return;
        }
        return iconEl.dataset?.icon?.includes(className);
    }
}
registry.category("builder-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
