import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { GridColumnsOption } from "./grid_column_option";
import { withSequence } from "@html_editor/utils/resource";
import { GRID_COLUMNS } from "@website/builder/option_sequence";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";

export class GridColumnsOptionPlugin extends Plugin {
    static id = "GridColumnsOption";
    resources = {
        builder_options: [withSequence(GRID_COLUMNS, GridColumnsOption)],
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
