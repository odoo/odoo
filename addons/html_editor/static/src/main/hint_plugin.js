import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock, isProtected } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { closestBlock } from "../utils/blocks";

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
        normalize_handlers: this.normalize.bind(this),
        clean_for_save_handlers: ({ root }) => this.clearHints(root),
        content_updated_handlers: this.updateHints.bind(this),

        system_classes: ["o-we-hint"],
        system_attributes: ["o-we-hint-text"],
    };

    setup() {
        this.updateHints(this.editable);
    }

    destroy() {
        super.destroy();
        this.clearHints();
    }

    normalize() {
        this.hint = null;
        this.clearHints();
        this.updateHints();
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
            for (const cb of this.getResource("hint_targets_providers")) {
                for (const target of cb(selectionData, this.editable)) {
                    const nodeHint = hints.find((h) => target.matches(h.selector))?.text;
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
            if (!selectionData.documentSelectionIsInEditable) {
                return;
            }
            for (const hint of hints) {
                if (hint.selector) {
                    if (
                        blockEl?.matches(hint.selector) &&
                        !isProtected(blockEl) &&
                        isEmptyBlock(blockEl)
                    ) {
                        this.makeHint(blockEl, hint.text);
                    }
                }
            }
        }
    }

    makeHint(el, text) {
        this.dispatchTo("make_hint_handlers", el);
        el.setAttribute("o-we-hint-text", text);
        el.classList.add("o-we-hint");
    }

    removeHint(el) {
        el.removeAttribute("o-we-hint-text");
        removeClass(el, "o-we-hint");
        this.getResource("system_style_properties").forEach((n) => el.style.removeProperty(n));
    }

    clearHints(root = this.editable) {
        for (const elem of selectElements(root, ".o-we-hint")) {
            this.removeHint(elem);
        }
    }
}
