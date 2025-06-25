import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { registry } from "@web/core/registry";
import { addBackgroundGrid, setElementToMaxZindex } from "@html_builder/utils/grid_layout_utils";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";

class SpacingOptionPlugin extends Plugin {
    static id = "SpacingOption";
    resources = {
        builder_actions: {
            SetGridSpacingAction,
        },
        savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
        on_cloned_handlers: this.onCloned.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    isMutationRecordSavable(record) {
        // Do not consider the grid preview in the history.
        if (record.type === "childList") {
            const node = record.addedNodes[0] || record.removedNodes[0];
            if (node.matches && node.matches(".o_we_grid_preview") && isBlock(node)) {
                return false;
            }
        }
        if (record.type === "attributes") {
            if (record.target.matches(".o_we_grid_preview")) {
                return false;
            }
        }
        return true;
    }

    removeGridPreviews(el) {
        el.querySelectorAll(".o_we_grid_preview").forEach((gridPreviewEl) =>
            gridPreviewEl.remove()
        );
    }

    onCloned({ cloneEl }) {
        this.removeGridPreviews(cloneEl);
    }

    cleanForSave({ root }) {
        this.removeGridPreviews(root);
    }
}

registry.category("website-plugins").add(SpacingOptionPlugin.id, SpacingOptionPlugin);

export class SetGridSpacingAction extends StyleAction {
    static id = "setGridSpacing";
    apply({ editingElement: rowEl }) {
        // Remove the grid preview if any.
        let gridPreviewEl = rowEl.querySelector(".o_we_grid_preview");
        if (gridPreviewEl) {
            gridPreviewEl.remove();
        }
        // Apply the style action on the grid gaps.
        super.apply(...arguments);
        // Add an animated grid preview.
        gridPreviewEl = addBackgroundGrid(rowEl, 0);
        gridPreviewEl.classList.add("o_we_grid_preview");
        setElementToMaxZindex(gridPreviewEl, rowEl);
        gridPreviewEl.addEventListener("animationend", () => gridPreviewEl.remove());
    }
}
