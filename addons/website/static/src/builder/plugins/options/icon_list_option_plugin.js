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
    static dependencies = ["icon"];

    load({ editingElement }) {
        return this.dependencies.icon.pickIcon({ target: editingElement });
    }

    apply({ editingElement, loadResult: savedIconEl }) {
        if (!savedIconEl) {
            return;
        }
        // Temporarily add the icon to the DOM to read its unicode.
        savedIconEl.style.display = "none";
        editingElement.appendChild(savedIconEl);
        // The content is `"name" / ""`: the list takes the name and adds its
        // own alternative text.
        const iconContent = getComputedStyle(savedIconEl, "::before").content.split("/")[0].trim();
        editingElement.removeChild(savedIconEl);
        editingElement.style.setProperty("--icon-list-icon-content", iconContent);
    }
}

registry.category("website-plugins").add(IconListOptionPlugin.id, IconListOptionPlugin);
