import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { GridColumnsOption } from "./grid_column_option";

export class GridColumnsOptionPlugin extends Plugin {
    static id = "GridColumnsOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            {
                OptionComponent: GridColumnsOption,
                selector: ".row:not(.s_col_no_resize) > div",
            },
        ],
        builder_actions: this.getActions(),
        system_classes: ["o_we_padding_highlight"],
        on_clone_handlers: ({ cloneEl }) => {
            if (cloneEl.matches(".o_we_padding_highlight")) {
                cloneEl.classList.remove("o_we_padding_highlight");
            }
            cloneEl.querySelectorAll(".o_we_padding_highlight").forEach((el) => {
                el.classList.remove("o_we_padding_highlight");
            });
        },
    };

    getActions() {
        const builderActions = this.dependencies.builderActions;
        return {
            get setGridColumnsPadding() {
                const styleAction = builderActions.getAction("styleAction");
                const removeHighlightClass = ({ target: editingElement }) => {
                    editingElement.classList.remove("o_we_padding_highlight");
                    editingElement.removeEventListener("animationend", removeHighlightClass);
                };
                return {
                    ...styleAction,
                    apply: (...args) => {
                        const { editingElement } = args[0];
                        removeHighlightClass({ target: editingElement });
                        styleAction.apply(...args);
                        editingElement.classList.add("o_we_padding_highlight");
                        editingElement.addEventListener("animationend", removeHighlightClass);
                    },
                };
            },
        };
    }
}

registry.category("website-plugins").add(GridColumnsOptionPlugin.id, GridColumnsOptionPlugin);
