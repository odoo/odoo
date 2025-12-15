import { Plugin } from "@html_editor/plugin";
import { isEditorTab, isEmptyBlock, isProtected } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { closestBlock } from "../utils/blocks";

/**
 * @typedef {import("@html_editor/editor").EditorContext} EditorContext
 * @typedef {import("@html_editor/core/selection_plugin").SelectionData} SelectionData
 * @typedef {import("plugins").CSSSelector} CSSSelector
 * @typedef {import("plugins").TranslatedString} TranslatedString
 */

/**
 * @typedef {((
 *   selectionData: SelectionData,
 *   editable: EditorContext["editable"]
 * ) => HTMLElement[] | NodeList)[]} hint_targets_providers
 * @typedef {{ selector: CSSSelector; text: TranslatedString; }[]} hints
 */

export class HintPlugin extends Plugin {
    static id = "hint";
    static dependencies = ["history", "selection"];
    /** @type {import("plugins").EditorResources} */
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

        hint_targets_providers: (selectionData, editable) => {
            if (!selectionData.currentSelectionIsInEditable || !selectionData.documentSelection) {
                return [];
            }
            const blockEl = closestBlock(selectionData.documentSelection.anchorNode);
            if (this.dependencies.selection.isNodeEditable(blockEl)) {
                return [blockEl];
            } else {
                return [];
            }
        },
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
        this.clearHints();
        this.updateHints();
    }

    /**
     * @param {HTMLElement} [root]
     */
    updateHints() {
        const selectionData = this.dependencies.selection.getSelectionData();
        const editableSelection = selectionData.editableSelection;
        this.clearHints();
        if (editableSelection.isCollapsed) {
            const hints = this.getResource("hints");
            for (const provideTargets of this.getResource("hint_targets_providers")) {
                for (const target of provideTargets(selectionData, this.editable)) {
                    const nodeHint = hints.find((h) => target.matches(h.selector))?.text;
                    if (
                        target &&
                        nodeHint &&
                        isEmptyBlock(target) &&
                        !isProtected(target) &&
                        !descendants(target).some(isEditorTab)
                    ) {
                        this.makeHint(target, nodeHint);
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
