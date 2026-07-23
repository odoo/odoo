import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class IconListOptionPlugin extends Plugin {
    static id = "iconListOption";
    resources = {
        so_content_addition_selectors: [".s_icon_list"],
        builder_actions: {
            ReplaceListIconAction,
        },
    };
}

export class ReplaceListIconAction extends BuilderAction {
    static id = "replaceListIcon";
    static dependencies = ["media"];

    load() {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                visibleTabs: ["ICONS"],
                save: resolve,
            });
            onClose.then(() => resolve());
        });
    }

    apply({ editingElement, loadResult: savedIconEl }) {
        if (!savedIconEl) {
            return;
        }
        const iconName = savedIconEl.getAttribute("data-icon");
        const isFilled = savedIconEl.classList.contains("oi-filled");
        const iconContent = `"${iconName}${isFilled ? "_f" : ""}"`;
        editingElement.style.setProperty("--icon-list-icon-content", iconContent);
    }
}

registry.category("website-plugins").add(IconListOptionPlugin.id, IconListOptionPlugin);
