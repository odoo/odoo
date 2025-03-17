import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock, isProtected } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { childNodes, selectElements } from "@html_editor/utils/dom_traversal";
import { closestBlock } from "../utils/blocks";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";

function isMutationRecordSavable(record) {
    return !(record.type === "attributes" && record.attributeName === "placeholder");
}

export class HintPlugin extends Plugin {
    static id = "hint";
    static dependencies = ["history", "selection"];
    resources = {
        /** Handlers */
        selectionchange_handlers: this.updateHints.bind(this),
        external_history_step_handlers: () => {
            this.clearHints();
            this.updateHints();
        },
        clean_handlers: this.clearHints.bind(this),
        clean_for_save_handlers: ({ root }) => this.clearHints(root),
        content_updated_handlers: this.updateHints.bind(this),

        savable_mutation_record_predicates: isMutationRecordSavable,
        system_classes: ["o-we-hint"],
        ...(this.config.placeholder && {
            hints: [
                {
                    text: this.config.placeholder,
                    target: (selectionData, editable) => {
                        if (
                            selectionData.documentSelectionIsInEditable ||
                            childNodes(editable).length !== 1
                        ) {
                            return;
                        }
                        const el = editable.firstChild;
                        if (isEmptyBlock(el) && el.matches(baseContainerGlobalSelector)) {
                            return el;
                        }
                    },
                },
            ],
        }),
    };

    setup() {
        this.hint = null;
        this.updateHints(this.editable);
    }

    destroy() {
        super.destroy();
        this.clearHints();
    }

    /**
     * @param {HTMLElement} [root]
     */
    updateHints() {
        const selectionData = this.dependencies.selection.getSelectionData();
        const editableSelection = selectionData.editableSelection;
        if (this.hint) {
            const blockEl = closestBlock(editableSelection.anchorNode);
            this.removeHint(this.hint);
            this.removeHint(blockEl);
        }
        if (editableSelection.isCollapsed) {
            for (const hint of this.getResource("hints")) {
                if (hint.selector) {
                    const el = closestBlock(editableSelection.anchorNode);
                    if (el && el.matches(hint.selector) && !isProtected(el) && isEmptyBlock(el)) {
                        this.makeHint(el, hint.text);
                        this.hint = el;
                    }
                } else {
                    const target = hint.target(selectionData, this.editable);
                    // Do not replace an existing empty block hint by a temp hint.
                    if (target && !target.classList.contains("o-we-hint")) {
                        this.makeHint(target, hint.text);
                        this.hint = target;
                        return;
                    }
                }
            }
        }
    }

    makeHint(el, text) {
        el.setAttribute("placeholder", text);
        el.classList.add("o-we-hint");
    }

    removeHint(el) {
        el.removeAttribute("placeholder");
        removeClass(el, "o-we-hint");
        if (this.hint === el) {
            this.hint = null;
        }
    }

    clearHints(root = this.editable) {
        for (const elem of selectElements(root, ".o-we-hint")) {
            this.removeHint(elem);
        }
    }
}
