import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";

export class GridColumnsOptionPlugin extends Plugin {
    static id = "GridColumnsOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetGridColumnsPaddingAction,
        },
        system_classes: ["o_we_padding_highlight"],
    };
}

registry.category("website-plugins").add(GridColumnsOptionPlugin.id, GridColumnsOptionPlugin);

const removePaddingPreview = (event) => {
    const editingElement = event.target;
    editingElement.classList.remove("o_we_padding_highlight");
    editingElement.removeEventListener("animationend", removePaddingPreview);
};
export class SetGridColumnsPaddingAction extends StyleAction {
    static id = "setGridColumnsPadding";
    apply(...args) {
        const { editingElement } = args[0];
        removePaddingPreview({ target: editingElement });
        super.apply(...args);
        editingElement.classList.add("o_we_padding_highlight");
        editingElement.addEventListener("animationend", removePaddingPreview);
    }
}
