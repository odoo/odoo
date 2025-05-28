import { before } from "@html_builder/utils/option_sequence";
import { WIDTH } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { fonts } from "@html_editor/utils/fonts";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class AlertOptionPlugin extends Plugin {
    static id = "alertOption";
    resources = {
        builder_actions: {
            alertIcon: {
                apply: ({ editingElement, params: { mainParam: className } }) => {
                    const icon = editingElement.querySelector(".s_alert_icon");
                    if (!icon) {
                        return;
                    }
                    fonts.computeFonts();
                    const allFaIcons = fonts.fontIcons[0].alias;
                    icon.classList.remove(...allFaIcons);
                    icon.classList.add(className);
                },
                clean: ({ editingElement, params: { mainParam: className } }) => {
                    const icon = editingElement.querySelector(".s_alert_icon");
                    if (!icon) {
                        return;
                    }
                    icon.classList.remove(className);
                },
                isApplied: ({ editingElement, params: { mainParam: className } }) => {
                    const iconEl = editingElement.querySelector(".s_alert_icon");
                    if (!iconEl) {
                        return;
                    }
                    return iconEl.classList.contains(className);
                },
            },
        },
        builder_options: [
            withSequence(before(WIDTH), {
                template: "website.AlertOption",
                selector: ".s_alert",
            }),
        ],
        so_content_addition_selector: [".s_alert"],
    };
}
registry.category("website-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
