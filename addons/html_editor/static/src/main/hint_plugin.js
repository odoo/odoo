import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock, isProtected } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { selectElements } from "@html_editor/utils/dom_traversal";
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
        return [];
    }
    const el = editable.firstChild;
    if (el.tagName === "P" && isEmptyBlock(el)) {
        return [el];
    }
    return [];
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
            hints: { text: this.config.placeholder, target },
        }),
    };

    setup() {
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
        const blockEl = closestBlock(editableSelection.anchorNode);
        this.removeHint(blockEl);
        this.clearHints();
        if (editableSelection.isCollapsed) {
            const hints = this.getResource("hints");
            for (const hint of hints) {
                if (hint.selector) {
                    if (
                        blockEl?.matches(hint.selector) &&
                        !isProtected(blockEl) &&
                        isEmptyBlock(blockEl)
                    ) {
                        this.makeHint(blockEl, hint.text);
                    }
                } else {
                    const targets = hint.target(selectionData, this.editable);
                    for (const target of targets) {
                        const nodeHint =
                            target.tagName === "P"
                                ? hint.text
                                : hints.find((h) => target.matches(h.selector))?.text ?? hint.text;
                        if (
                            target &&
                            !target.classList.contains("o-we-hint") &&
                            nodeHint &&
                            isEmptyBlock(target)
                        ) {
                            this.makeHint(target, nodeHint);
                        }
                    }
                }
            }
        }
    }

    makeHint(el, text) {
        this.dispatchTo("make_hint_handlers", el);
        el.setAttribute("placeholder", text);
        el.classList.add("o-we-hint");
    }

    removeHint(el) {
        el.removeAttribute("placeholder");
        removeClass(el, "o-we-hint");
        this.getResource("system_style_properties").forEach((n) => el.style.removeProperty(n));
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
