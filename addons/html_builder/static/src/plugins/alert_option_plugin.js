import { before, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { fonts } from "@html_editor/utils/fonts";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

class AlertOptionPlugin extends Plugin {
    static id = "alertOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            AlertIconAction,
        },
        builder_options: [withSequence(before(WIDTH), AlertOption)],
        so_content_addition_selector: [".s_alert"],
    };
}

export class AlertOption extends BaseOptionComponent {
    static template = "html_builder.AlertOption";
    static selector = ".s_alert";
    static name = "alertTypeOption";
}

export class AlertIconAction extends BuilderAction {
    static id = "alertIcon";
    apply({ editingElement, params: { mainParam: className } }) {
        const icon = editingElement.querySelector(".s_alert_icon");
        if (!icon) {
            return;
        }
        fonts.computeFonts();
        const allFaIcons = fonts.fontIcons[0].alias;
        icon.classList.remove(...allFaIcons);
        icon.classList.add(className);
    }
    clean({ editingElement, params: { mainParam: className } }) {
        const icon = editingElement.querySelector(".s_alert_icon");
        if (!icon) {
            return;
        }
        icon.classList.remove(className);
    }
    isApplied({ editingElement, params: { mainParam: className } }) {
        const iconEl = editingElement.querySelector(".s_alert_icon");
        if (!iconEl) {
            return;
        }
        return iconEl.classList.contains(className);
    }
}
registry.category("builder-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
