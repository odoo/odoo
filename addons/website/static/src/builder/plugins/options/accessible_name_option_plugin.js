import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class AccessibleNameAction extends BuilderAction {
    static id = "accessibleName";
    static dependencies = ["websiteBridge"];

    getValue({ editingElement }) {
        return editingElement.dataset.accessibleName || this.getDefaultName(editingElement);
    }
    apply({ editingElement, value }) {
        value = value.trim();
        if (value && value !== this.getDefaultName(editingElement)) {
            editingElement.dataset.accessibleName = value;
        } else {
            delete editingElement.dataset.accessibleName;
        }
    }
    getDefaultName(editingElement) {
        // Each snippet registers `{ selector, getDefaultName }` in the page,
        // so that the default is in the website's language
        return this.dependencies.websiteBridge
            .getRegistry()
            .category("website.accessible_names")
            .getAll()
            .find(({ selector }) => editingElement.matches(selector))
            .getDefaultName(editingElement);
    }
}

export class AccessibleNameOptionPlugin extends Plugin {
    static id = "accessibleNameOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: { AccessibleNameAction },
    };
}

registry.category("website-plugins").add(AccessibleNameOptionPlugin.id, AccessibleNameOptionPlugin);
