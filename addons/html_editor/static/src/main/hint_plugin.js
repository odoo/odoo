import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock, isProtected } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { closestBlock } from "../utils/blocks";

function isMutationRecordSavable(record) {
    return !(record.type === "attributes" && record.attributeName === "placeholder");
}

/**
 * @param {SelectionData} selectionData
 * @param {HTMLElement} editable
 */
function target(selectionData, editable) {
    if (selectionData.documentSelectionIsInEditable || editable.childNodes.length !== 1) {
        return;
    }
    const el = editable.firstChild;
    if (el.tagName === "P" && isEmptyBlock(el)) {
        return el;
    }
}

export class HintPlugin extends Plugin {
    static name = "hint";
    static dependencies = ["history", "selection"];
    resources = {
        mutation_filtered_classes: ["o-we-hint"],
        is_mutation_record_savable: isMutationRecordSavable,
        onSelectionChange: this.updateHints.bind(this),
        onExternalHistorySteps: () => {
            this.clearHints();
            this.updateHints();
        },
        ...(this.config.placeholder && {
            hints: [
                {
                    text: this.config.placeholder,
                    target,
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

    handleCommand(command, payload) {
        switch (command) {
            case "CONTENT_UPDATED": {
                this.updateHints(payload.root);
                break;
            }
            case "CLEAN":
            case "CLEAN_FOR_SAVE":
                this.clearHints(payload.root);
                break;
        }
    }

    /**
     * @param {HTMLElement} [root]
     */
    updateHints() {
        const selectionData = this.shared.getSelectionData();
        const editableSelection = selectionData.editableSelection;
        const blockEl = closestBlock(editableSelection.anchorNode);
        if (this.hint) {
            this.removeHint(this.hint);
            this.removeHint(blockEl);
        }
        if (editableSelection.isCollapsed) {
            const columnContainer = closestElement(editableSelection.anchorNode, ".o_text_columns");
            if (columnContainer) {
                this.hint = [];
            }
            for (const hint of this.getResource("hints")) {
                if (hint.selector) {
                    if (columnContainer) {
                        for (const elem of selectElements(
                            columnContainer,
                            `${hint.selector}:first-child`
                        )) {
                            // Apply helper hint on first block element of each column
                            if (
                                elem.closest("div[class^='col-']") ===
                                    closestElement(
                                        editableSelection.anchorNode,
                                        "div[class^='col-']"
                                    ) &&
                                blockEl !== elem
                            ) {
                                // If cursor is not inside first block element but a different
                                // one, skip that first element.
                                continue;
                            }
                            if (!isProtected(elem) && isEmptyBlock(elem)) {
                                this.makeHint(elem, hint.text);
                                this.hint.push(elem);
                            }
                        }
                    }
                    if (
                        blockEl &&
                        blockEl.matches(hint.selector) &&
                        !isProtected(blockEl) &&
                        isEmptyBlock(blockEl)
                    ) {
                        this.makeHint(blockEl, hint.text);
                        Array.isArray(this.hint) ? this.hint.push(blockEl) : (this.hint = blockEl);
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
        if (Array.isArray(el)) {
            el.forEach((e) => {
                e.removeAttribute("placeholder");
                removeClass(e, "o-we-hint");
            });
        } else {
            el.removeAttribute("placeholder");
            removeClass(el, "o-we-hint");
        }
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
