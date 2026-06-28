import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { registry } from "@web/core/registry";
import { addBackgroundGrid, setElementToMaxZindex } from "@html_builder/utils/grid_layout_utils";
import { StyleAction } from "@html_builder/core/core_builder_action_plugin";
import { NATIVE_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";

export class SpacingOptionPlugin extends Plugin {
    static id = "SpacingOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetGridSpacingAction,
        },
        is_mutation_savable_predicates: this.isMutationSavable.bind(this),
        on_cloned_handlers: this.onCloned.bind(this),
        clean_for_save_processors: this.cleanForSave.bind(this),
    };

    /**
     * @param {import("@html_editor/core/dom_observer_plugin").NativeMutation} mutation
     * @returns {boolean | undefined}
     */
    isMutationSavable(mutation) {
        // Do not consider the grid preview in the history.
        if (mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST) {
            const node = mutation.addedNodes[0] || mutation.removedNodes[0];
            if (node?.matches?.(".o_we_grid_preview") && isBlock(node)) {
                return false;
            }
        }
        if (mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES) {
            if (mutation.target.matches(".o_we_grid_preview")) {
                return false;
            }
        }
    }

    removeGridPreviews(el) {
        el.querySelectorAll(".o_we_grid_preview").forEach((gridPreviewEl) =>
            gridPreviewEl.remove()
        );
    }

    onCloned({ cloneEl }) {
        this.removeGridPreviews(cloneEl);
    }

    cleanForSave(root) {
        this.removeGridPreviews(root);
        return root;
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
