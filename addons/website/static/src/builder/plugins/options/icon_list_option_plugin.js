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
        // Temporarily add the icon to the DOM to read its unicode.
        savedIconEl.style.display = "none";
        editingElement.appendChild(savedIconEl);
        const iconContent = getComputedStyle(savedIconEl, "::before").content;
        editingElement.removeChild(savedIconEl);
        // Convert the raw character to a readable "\fXXX" CSS escape.
        const char = iconContent.slice(1, -1);
        const iconUnicode = `"\\${char.charCodeAt(0).toString(16)}"`;
        editingElement.style.setProperty("--icon-list-icon-content", iconUnicode);
    }
}

registry.category("website-plugins").add(IconListOptionPlugin.id, IconListOptionPlugin);
