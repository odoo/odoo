import { Plugin } from "@html_editor/plugin";
import { fonts } from "@html_editor/utils/fonts";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class AlertOptionPlugin extends Plugin {
    static id = "alertOption";
    resources = {
        builder_actions: {
            alertIcon: {
                apply: ({ editingElement, param: { mainParam: className } }) => {
                    const icon = editingElement.querySelector(".s_alert_icon");
                    if (!icon) {
                        return;
                    }
                    fonts.computeFonts();
                    const allFaIcons = fonts.fontIcons[0].alias;
                    icon.classList.remove(...allFaIcons);
                    icon.classList.add(className);
                },
                clean: ({ editingElement, param: { mainParam: className } }) => {
                    const icon = editingElement.querySelector(".s_alert_icon");
                    if (!icon) {
                        return;
                    }
                    icon.classList.remove(className);
                },
                isApplied: ({ editingElement, param: { mainParam: className } }) => {
                    const iconEl = editingElement.querySelector(".s_alert_icon");
                    if (!iconEl) {
                        return;
                    }
                    return iconEl.classList.contains(className);
                },
            },
        },
        builder_options: [
            withSequence(5, {
                template: "html_builder.AlertOption",
                selector: ".s_alert",
            }),
        ],
    };
}
registry.category("website-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
