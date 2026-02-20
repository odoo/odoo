import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ListGroupOption extends BaseOptionComponent {
    static template = "website.ListGroupOption";
    static selector = ".s_list_group";
}

class ListGroupOptionPlugin extends Plugin {
    static id = "listGroupOptionPlugin";
    resources = {
        builder_options: [ListGroupOption],
        so_content_addition_selector: [".s_list_group"],
        builder_actions: {
            ReplaceListIconAction,
        },
    };
}

export class ReplaceListIconAction extends BuilderAction {
    static id = "replaceListIcon";
    static dependencies = ["media"];
    async load() {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                visibleTabs: ["ICONS"],
                save: (iconEl) => resolve(iconEl),
            });
            onClose.then(resolve);
        });
    }
    apply({ editingElement, loadResult: savedIconEl }) {
        if (!savedIconEl) {
            return;
        }
        const tempEl = this.document.createElement("span");
        tempEl.className = savedIconEl.className;
        tempEl.style.display = "none";
        // temporarily add to get the icon unicode
        editingElement.appendChild(tempEl);
        const iconUnicode = window
            .getComputedStyle(tempEl, "::before")
            .content.replace(/['"]/g, "");
        editingElement.removeChild(tempEl);
        editingElement.style.setProperty("--s_list_group-icon-content", `"${iconUnicode}"`);
    }
}

registry.category("website-plugins").add(ListGroupOptionPlugin.id, ListGroupOptionPlugin);
