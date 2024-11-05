import { Plugin } from "@html_editor/plugin";
import { SAVABLE_SELECTOR } from "../../utils";
export class HandleDirtyElementPlugin extends Plugin {
    static id = "dirty";
    static shared = ["handleDirtyElement", "isEditableDirty"];
    resources = {
        handleNewRecords: this.handleMutations,
    };

    handleDirtyElement(dirtyEl) {
        dirtyEl.classList.remove("o_dirty");
        const el = dirtyEl.cloneNode(true);
        this.dispatchTo("clean_for_save_handlers", { root: el });
        return el;
    }

    /**
     * Handles the flag of the closest savable element to the mutation as dirty
     *
     * @param {Object} records - The observed mutations
     * @param {String} currentOperation - The name of the current operation
     */
    handleMutations(records, currentOperation) {
        if (currentOperation === "undo" || currentOperation === "redo") {
            // Do nothing as `o_dirty` has already been handled by the history
            // plugin.
            return;
        }
        for (const record of records) {
            if (record.attributeName === "contenteditable") {
                continue;
            }
            let targetEl = record.target;
            if (!targetEl.isConnected) {
                continue;
            }
            if (targetEl.nodeType !== Node.ELEMENT_NODE) {
                targetEl = targetEl.parentElement;
            }
            if (!targetEl) {
                continue;
            }
            const savableEl = targetEl.closest(SAVABLE_SELECTOR);
            if (
                !savableEl ||
                savableEl.classList.contains("o_dirty") ||
                savableEl.hasAttribute("data-oe-readonly")
            ) {
                continue;
            }
            savableEl.classList.add("o_dirty");
        }
    }

    isEditableDirty() {
        return !!this.editable.querySelector(".o_dirty");
    }
}
