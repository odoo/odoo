import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { GridColumnsOption } from "./grid_column_option";
import { withSequence } from "@html_editor/utils/resource";
import { GRID_COLUMNS } from "@website/website_builder/option_sequence";

export class GridColumnsOptionPlugin extends Plugin {
    static id = "GridColumnsOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            withSequence(GRID_COLUMNS, {
                OptionComponent: GridColumnsOption,
                selector: ".row:not(.s_col_no_resize) > div",
            }),
        ],
        builder_actions: this.getActions(),
        system_classes: ["o_we_padding_highlight"],
    };

    getActions() {
        const builderActions = this.dependencies.builderActions;
        return {
            get setGridColumnsPadding() {
                const styleAction = builderActions.getAction("styleAction");
                const removePaddingPreview = ({ target: editingElement }) => {
                    editingElement.classList.remove("o_we_padding_highlight");
                    editingElement.removeEventListener("animationend", removePaddingPreview);
                };
                return {
                    ...styleAction,
                    apply: (...args) => {
                        const { editingElement } = args[0];
                        removePaddingPreview({ target: editingElement });
                        styleAction.apply(...args);
                        editingElement.classList.add("o_we_padding_highlight");
                        editingElement.addEventListener("animationend", removePaddingPreview);
                    },
                };
            },
        };
    }
}

registry.category("website-plugins").add(GridColumnsOptionPlugin.id, GridColumnsOptionPlugin);
