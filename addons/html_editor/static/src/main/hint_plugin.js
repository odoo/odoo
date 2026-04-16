import { Plugin } from "@html_editor/plugin";
import { isEditorTab, isEmptyBlock, isProtected } from "@html_editor/utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import {
    closestElement,
    descendants,
    firstLeaf,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { closestBlock } from "../utils/blocks";
import { debounce } from "@web/core/utils/timing";

/**
 * @typedef {import("@html_editor/editor").EditorContext} EditorContext
 * @typedef {import("@html_editor/core/selection_plugin").SelectionData} SelectionData
 * @typedef {import("plugins").CSSSelector} CSSSelector
 * @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString
 */

/**
 * @typedef {((
 *   selectionData: SelectionData,
 *   editable: EditorContext["editable"]
 * ) => HTMLElement[] | NodeList)[]} hint_targets_providers
 * @typedef {{ selector: CSSSelector; text: LazyTranslatedString; }[]} hints
 */

export class HintPlugin extends Plugin {
    static id = "hint";
    static dependencies = ["history", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        /** Handlers */
        on_selectionchange_handlers: this.triggerDebouncedUpdateHints.bind(this),
        on_external_history_step_added_handlers: () => {
            this.clearHints();
            this.updateHints();
        },
        on_content_updated_handlers: this.updateHints.bind(this),

        /** Predicates */
        should_show_power_buttons_predicates: ({ anchorNode }) => {
            if (!closestElement(anchorNode, ".o-we-hint")) {
                return false;
            }
        },

        /** Processors */
        clean_for_save_processors: (root) => this.clearHints(root),
        normalize_processors: this.normalize.bind(this),

        /** Providers */
        hint_targets_providers: (selectionData, editable) => {
            if (
                !(
                    selectionData.documentSelectionIsInEditable &&
                    this.dependencies.selection.editableDocumentHasFocus()
                ) ||
                !selectionData.documentSelection
            ) {
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
        const shouldDebounce = this.config.debounceHints !== false;
        if (shouldDebounce) {
            this.debouncedUpdateHints = debounce(this.updateHints.bind(this), 30);
        } else {
            this.debouncedUpdateHints = this.updateHints.bind(this);
        }
    }

    destroy() {
        super.destroy();
        this.clearHints();
    }

    normalize() {
        this.clearHints();
        this.updateHints();
    }

    triggerDebouncedUpdateHints(selectionData = this.dependencies.selection.getSelectionData()) {
        if (selectionData.documentSelectionIsInEditable) {
            this.clearHints();
        }
        this.debouncedUpdateHints();
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
                    if (target && nodeHint && this.shouldDisplayHint(target)) {
                        this.makeHint(target, nodeHint);
                    }
                }
            }
        }
    }

    shouldDisplayHint(el) {
        let shouldDisplay =
            isEmptyBlock(el) && !isProtected(el) && !descendants(el).some(isEditorTab);
        if (shouldDisplay && el.childNodes.length) {
            // Do not display hints if font sizes have been adjusted
            const elStyle = getComputedStyle(el);
            const hintFontSize = parseInt(elStyle.fontSize);
            const childStyle = getComputedStyle(firstLeaf(el).parentElement);
            const childFontSize = parseInt(childStyle.fontSize);
            shouldDisplay = childFontSize === hintFontSize;
        }
        return shouldDisplay;
    }

    makeHint(el, text) {
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
