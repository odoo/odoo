import { ClassAction, StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class CardWidthOptionPlugin extends Plugin {
    static id = "cardWidthOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetCardWidthAction,
            SetCardAlignmentAction,
        },
    };
}

registry.category("website-plugins").add(CardWidthOptionPlugin.id, CardWidthOptionPlugin);

export class SetCardAlignmentAction extends ClassAction {
    static id = "setCardAlignment";
    isApplied({ editingElement: el, params: { mainParam: classNames } }) {
        if (classNames === "me-auto") {
            return !["mx-auto", "ms-auto"].some((cls) => el.classList.contains(cls));
        }
        return super.isApplied(...arguments);
    }
}

export class SetCardWidthAction extends StyleAction {
    static id = "setCardWidth";
    getValue(...args) {
        const value = super.getValue(...args);
        return value.includes("%") ? value : "100%";
    }
}
