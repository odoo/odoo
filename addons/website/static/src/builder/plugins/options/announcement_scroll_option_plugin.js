import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

class SetItemTextAction extends BuilderAction {
    static id = "setItemTextAction";
    static dependencies = ["edit_interaction"];

    getValue({ editingElement, params }) {
        return editingElement.textContent;
    }
    apply({ editingElement, value, params }) {
        editingElement.textContent = value;
    }
}

export class AnnouncementScrollOptionPlugin extends Plugin {
    static id = "announcementScrollOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetItemTextAction,
        },
    };
}

registry
    .category("website-plugins")
    .add(AnnouncementScrollOptionPlugin.id, AnnouncementScrollOptionPlugin);
