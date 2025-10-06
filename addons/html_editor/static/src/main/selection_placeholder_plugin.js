import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { fillEmpty } from "@html_editor/utils/dom";
import {
    allowsParagraphRelatedElements,
    isEmpty,
    isNotEditableNode,
} from "@html_editor/utils/dom_info";
import {
    closestElement,
    getAdjacentNextSiblings,
    getAdjacentPreviousSiblings,
} from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

const blinkerClass = "o-horizontal-caret";
const placeholderAttribute = "data-selection-placeholder";
const placeholderSelector = `[${placeholderAttribute}]`;
/**
 * @param {"before"|"after"} side
 * @param {Node} node
 * @returns {Node|undefined}
 */
const getNonWhitespaceSibling = (side, node) => {
    const siblings =
        side === "before" ? getAdjacentPreviousSiblings(node) : getAdjacentNextSiblings(node);
    return siblings.find(
        (sibling) => !(sibling.nodeType === Node.TEXT_NODE && !sibling.textContent.trim())
    );
};

export class SelectionPlaceholderPlugin extends Plugin {
    static id = "selectionPlaceholder";
    static dependencies = ["baseContainer", "history", "selection"];
    resources = {
        external_history_step_handlers: this.updatePlaceholders.bind(this),
        normalize_handlers: this.updatePlaceholders.bind(this),
        step_added_handlers: this.updatePlaceholders.bind(this),
        selectionchange_handlers: (selectionData) => this.onSelectionChange(selectionData),
        clean_for_save_handlers: withSequence(0, ({ root }) => {
            for (const placeholder of root.querySelectorAll(placeholderSelector)) {
                placeholder.remove();
            }
        }),
        split_element_block_overrides: ({ blockToSplit }) => {
            if (blockToSplit.hasAttribute(placeholderAttribute)) {
                this.persistPlaceholder(blockToSplit);
                return true;
            }
        },
        is_selection_blocker_predicates: isNotEditableNode,
        should_skip_node_predicates: (leaf) => closestElement(leaf, placeholderSelector),
        power_buttons_visibility_predicates: ({ anchorNode }) =>
            !closestElement(anchorNode, placeholderSelector),
        move_node_blacklist_selectors: placeholderSelector,
        system_classes: blinkerClass,
        uncrossable_context_blocks_providers: (root) => [
            root,
            ...root.querySelectorAll("*[contenteditable=true]"),
        ],
        is_safe_for_selection_placeholder_predicates: (blocker) =>
            blocker.parentElement.isContentEditable &&
            allowsParagraphRelatedElements(blocker.parentElement),
    };

    /**
     * Update all placeholders and blinker classes so they are present
     * everywhere we need them, and absent wherever they are not useful.
     */
    updatePlaceholders() {
        // 1. Persist placeholders.
        for (const placeholder of this.editable.querySelectorAll(placeholderSelector)) {
            if (
                !isEmpty(placeholder) ||
                (!placeholder.previousSibling && !placeholder.nextSibling)
            ) {
                this.persistPlaceholder(placeholder);
            }
        }
        // 2. Remove illegitimate placeholders.
        for (const placeholder of this.editable.querySelectorAll(placeholderSelector)) {
            const siblings = [
                getNonWhitespaceSibling("before", placeholder),
                getNonWhitespaceSibling("after", placeholder),
            ];
            if (!siblings.every((sibling) => !sibling || this.isSelectionBlocker(sibling))) {
                placeholder.remove();
            }
        }
        // 3. Add placeholders before and after every blocker where necessary.
        const uncrossableContextBlocks = this.getResource(
            "uncrossable_context_blocks_providers"
        ).flatMap((p) => p(this.editable));
        const blockers = [
            ...new Set(uncrossableContextBlocks.flatMap((element) => [...element.children])),
        ].filter(this.isSelectionBlocker.bind(this));
        const predicates = this.getResource("is_safe_for_selection_placeholder_predicates");
        for (const blocker of blockers) {
            for (const side of ["before", "after"]) {
                // Get the first non-whitespace sibling.
                const sibling = getNonWhitespaceSibling(side, blocker);
                // Insert a placeholder if there is no such sibling or if it's a
                // selection blocker.
                if (
                    (!sibling || this.isSelectionBlocker(sibling)) &&
                    predicates.every((predicate) => predicate(blocker, sibling))
                ) {
                    const placeholder = this.dependencies.baseContainer.createBaseContainer();
                    fillEmpty(placeholder);
                    placeholder.setAttribute(placeholderAttribute, "");
                    blocker[side](placeholder);
                }
            }
        }
        // 4. Reset blinker classes.
        this.resetBlinkerClasses();
    }

    /**
     * Turn a selection placeholder into a real block.
     *
     * @param {Element} placeholder
     */
    persistPlaceholder(placeholder) {
        placeholder.removeAttribute(placeholderAttribute);
        if (placeholder.className === blinkerClass) {
            placeholder.removeAttribute("class");
        } else {
            placeholder.classList.remove(blinkerClass);
        }
    }

    /**
     * Return true if the given node is a selection blocker, false otherwise. A
     * selection blocker is a node that can't be at the edge or the editor or
     * following another selection blocker, lest the selection cannot get past
     * it. Working around that problem is the purpose of this plugin.
     *
     * @param {Node} node
     * @returns {Boolean}
     */
    isSelectionBlocker(node) {
        return (
            !node.hasAttribute?.(placeholderAttribute) &&
            isBlock(node) &&
            this.getResource("is_selection_blocker_predicates").some((p) => p(node))
        );
    }

    /**
     * Remove any irrelevant blinker class (horizontal caret) and make sure
     * there is one on the placeholder in collapsed selection, if any.
     *
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     */
    resetBlinkerClasses(selection = this.dependencies.selection.getEditableSelection()) {
        const anchorPlaceholder =
            selection.isCollapsed && closestElement(selection.anchorNode, placeholderSelector);
        if (anchorPlaceholder) {
            anchorPlaceholder.classList.add(blinkerClass);
        }
        for (const blinker of this.editable.querySelectorAll(`.${blinkerClass}`)) {
            if (blinker !== anchorPlaceholder) {
                if (blinker.className === blinkerClass) {
                    blinker.removeAttribute("class");
                } else {
                    blinker.classList.remove(blinkerClass);
                }
            }
        }
    }

    /**
     * Update the placeholders' states in function of the selection, by
     * potentially persisting one, and by reseting the blinker classes.
     *
     * @param {import("@html_editor/core/selection_plugin").SelectionData} selectionData
     */
    onSelectionChange(selectionData) {
        const selection = selectionData.editableSelection;
        this.resetBlinkerClasses(selection);
        if (selection.isCollapsed) {
            const anchor = closestElement(selection.anchorNode);
            if (
                anchor?.hasAttribute(placeholderAttribute) &&
                !getNonWhitespaceSibling("next", anchor)
            ) {
                // If it's at the bottom of the document, just persist immediately.
                this.persistPlaceholder(anchor);
                this.dependencies.history.addStep();
            }
        }
    }
}
