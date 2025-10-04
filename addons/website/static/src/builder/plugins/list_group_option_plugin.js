import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ListGroupOptionPlugin extends Plugin {
    static id = "listGroupOptionPlugin";
    static dependencies = ["selection", "split"];
    resources = {
        builder_options: {
            template: "website.ListGroupOption",
            selector: ".s_list_group",
        },
        so_content_addition_selector: [".s_list_group"],
        builder_actions: {
            ReplaceListIconAction,
            IconBackgroundColor,
            IconColor,
        },
    };
}

export class ReplaceListIconAction extends BuilderAction {
    static id = "replaceListIcon";
    static dependencies = ["media"];
    async load() {
        return new Promise((resolve) => {
            const mediaDialogParams = {
                visibleTabs: ["ICONS"],
                save: (icon) => {
                    resolve(icon);
                },
            };
            const onClose = this.dependencies.media.openMediaDialog(mediaDialogParams);
            onClose.then(resolve);
        });
    }
    apply({ editingElement, loadResult: savedIconEl }) {
        if (!savedIconEl) {
            return;
        }
        editingElement.style.setProperty("--icon-content", `"${savedIconEl.dataset.unicode}"`);
    }
}

export class IconColor extends BuilderAction {
    static id = "iconColor";

    getValue({ editingElement }) {
        return editingElement
            ? getComputedStyle(editingElement).getPropertyValue("--icon-color").trim()
            : "";
    }

    apply({ editingElement, value }) {
        editingElement.style.setProperty("--icon-color", value);
    }
}

export class IconBackgroundColor extends BuilderAction {
    static id = "iconBackgroundColor";

    getValue({ editingElement }) {
        return editingElement
            ? getComputedStyle(editingElement).getPropertyValue("--icon-bg").trim()
            : "";
    }

    apply({ editingElement, value }) {
        editingElement.style.setProperty("--icon-bg", value);
    }
}

registry.category("website-plugins").add(ListGroupOptionPlugin.id, ListGroupOptionPlugin);
