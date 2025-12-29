import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
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

const BLINKER_CLASS = "o-horizontal-caret";
const PLACEHOLDER_ATTRIBUTE = "data-selection-placeholder";
const PLACEHOLDER_SELECTOR = `[${PLACEHOLDER_ATTRIBUTE}]`;

export class SelectionPlaceholderPlugin extends Plugin {
    static id = "selectionPlaceholder";
    static dependencies = ["baseContainer", "history", "selection"];
    resources = {
        external_history_step_handlers: this.updatePlaceholders.bind(this),
        normalize_handlers: withSequence(100, this.updatePlaceholders.bind(this)),
        step_added_handlers: this.updatePlaceholders.bind(this),
        selectionchange_handlers: (selectionData) => this.onSelectionChange(selectionData),
        clean_for_save_handlers: withSequence(0, ({ root }) => {
            for (const placeholder of root.querySelectorAll(PLACEHOLDER_SELECTOR)) {
                placeholder.remove();
            }
        }),
        split_element_block_overrides: ({ blockToSplit }) => {
            if (blockToSplit.hasAttribute(PLACEHOLDER_ATTRIBUTE)) {
                this.persistPlaceholder(blockToSplit);
                return true;
            }
        },
        selection_blocker_predicates: (blocker) => {
            if (
                (blocker.nodeType === Node.ELEMENT_NODE &&
                    blocker.hasAttribute(PLACEHOLDER_ATTRIBUTE)) ||
                !isBlock(blocker)
            ) {
                return false;
            } else if (isNotEditableNode(blocker)) {
                return true;
            }
        },
        selection_placeholder_container_predicates: (container) => {
            if (!container.isContentEditable || !allowsParagraphRelatedElements(container)) {
                return false;
            } else if (container.getAttribute("contenteditable") === "true") {
                return true;
            }
        },
        power_buttons_visibility_predicates: ({ anchorNode }) =>
            !closestElement(anchorNode, PLACEHOLDER_SELECTOR),
        move_node_blacklist_selectors: PLACEHOLDER_SELECTOR,
        system_node_selectors: PLACEHOLDER_SELECTOR,
        system_classes: BLINKER_CLASS,
    };

    setup() {
        this.addDomListener(
            this.editable,
            "focusout",
            () => this.editable.querySelectorAll(`.${BLINKER_CLASS}`).forEach(this.cleanBlinker),
            { isGlobal: true }
        );
        this.addDomListener(this.editable, "focusin", () => this.resetBlinkerClasses(), {
            isGlobal: true,
        });
    }

    /**
     * Update all placeholders and blinker classes so they are present
     * everywhere we need them, and absent wherever they are not useful.
     */
    updatePlaceholders() {
        const checkPredicate = (resourceId, node) => {
            const results = this.getResource(resourceId)
                .map((p) => p(node))
                .filter((result) => result !== undefined);
            return !!results.length && results.every(Boolean);
        };
        const isSelectionBlocker = (node) => checkPredicate("selection_blocker_predicates", node);
        const placeholderParents = [this.editable, ...this.editable.querySelectorAll("*")].filter(
            (container) => checkPredicate("selection_placeholder_container_predicates", container)
        );

        // 1. Update current placeholders.
        for (const placeholder of this.editable.querySelectorAll(PLACEHOLDER_SELECTOR)) {
            const siblings = ["before", "after"].map((side) =>
                getNonWhitespaceSibling(side, placeholder)
            );
            if (!isEmpty(placeholder) || !siblings.filter(Boolean).length) {
                // Persist non-empty placeholders and any suddenly lonely placeholder.
                this.persistPlaceholder(placeholder);
            } else if (
                !placeholderParents.includes(placeholder.parentElement) ||
                !siblings.every((sibling) => !sibling || isSelectionBlocker(sibling))
            ) {
                // Remove illegitimate placeholders.
                placeholder.remove();
            } else {
                // Update the margins.
                this.applyMargin(placeholder, ...siblings);
            }
        }

        // Get the blocks to check.
        const blockers = [
            ...new Set(placeholderParents.flatMap((element) => [...element.children])),
        ].filter((element) => isSelectionBlocker(element));

        // 2. Add placeholders before and after every blocker where necessary.
        for (const blocker of blockers) {
            for (const side of ["before", "after"]) {
                // Get the first non-whitespace sibling.
                const sibling = getNonWhitespaceSibling(side, blocker);
                // Insert a placeholder if there is no such sibling or if it's a
                // selection blocker.
                if (!sibling || isSelectionBlocker(sibling)) {
                    // Create the placeholder.
                    const placeholder = this.dependencies.baseContainer.createBaseContainer();
                    fillEmpty(placeholder);
                    placeholder.setAttribute(PLACEHOLDER_ATTRIBUTE, "");
                    // Position the placeholder.
                    const siblings = side === "before" ? [sibling, blocker] : [blocker, sibling];
                    this.applyMargin(placeholder, ...siblings);
                    // Insert the placeholder.
                    blocker[side](placeholder);
                }
            }
        }
        // 3. Reset blinker classes.
        this.resetBlinkerClasses();
    }

    /**
     * Position a placeholder between its siblings.
     *
     * @param {Element} placeholder
     * @param {Element} previous
     * @param {Element} next
     */
    applyMargin(placeholder, previous, next) {
        const marginBefore = previous ? getMargin(previous, "bottom") : 0;
        const marginAfter = next ? getMargin(next, "top") : 0;
        const middleMargin = Math.abs(marginBefore - marginAfter) / 2;
        if (middleMargin) {
            const positiveMargin = Math.abs(
                middleMargin - (marginAfter >= marginBefore ? marginAfter : marginBefore)
            );
            const negativeMargin = -1 - middleMargin;
            const marginTop = marginAfter >= marginBefore ? positiveMargin : negativeMargin;
            const marginBottom = marginAfter >= marginBefore ? negativeMargin : positiveMargin;
            placeholder.style.margin = `${marginTop}px 0 ${marginBottom}px`;
        }
    }

    /**
     * Turn a selection placeholder into a real block.
     *
     * @param {Element} placeholder
     */
    persistPlaceholder(placeholder) {
        placeholder.removeAttribute(PLACEHOLDER_ATTRIBUTE);
        this.cleanBlinker(placeholder);
        placeholder.removeAttribute("style");
    }

    /**
     * Remove the horizontal caret class from a placeholder element.
     *
     * @param {Element} blinker
     */
    cleanBlinker(blinker) {
        if (blinker.className === BLINKER_CLASS) {
            blinker.removeAttribute("class");
        } else {
            blinker.classList.remove(BLINKER_CLASS);
        }
    }

    /**
     * Remove any irrelevant blinker class (horizontal caret) and make sure
     * there is one on the placeholder in collapsed selection, if any.
     *
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     */
    resetBlinkerClasses(selection = this.dependencies.selection.getEditableSelection()) {
        const anchorPlaceholder =
            selection.isCollapsed && closestElement(selection.anchorNode, PLACEHOLDER_SELECTOR);
        if (anchorPlaceholder && this.document.activeElement.contains(anchorPlaceholder)) {
            anchorPlaceholder.classList.add(BLINKER_CLASS);
        }
        for (const blinker of this.editable.querySelectorAll(`.${BLINKER_CLASS}`)) {
            if (blinker !== anchorPlaceholder || !this.document.activeElement.contains(blinker)) {
                this.cleanBlinker(blinker);
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
                closestBlock(anchor.parentElement) === this.editable &&
                anchor?.hasAttribute(PLACEHOLDER_ATTRIBUTE) &&
                !getNonWhitespaceSibling("next", anchor)
            ) {
                // If it's at the bottom of the document, just persist immediately.
                this.persistPlaceholder(anchor);
                this.dependencies.history.addStep();
            }
        }
    }
}

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
/**
 * Get an element's top or bottom margin as a number.
 *
 * @param {Element} element
 * @param {"top"|"bottom"} side
 * @returns {Number}
 */
const getMargin = (element, side) =>
    +element.ownerDocument.defaultView
        .getComputedStyle(element)
        [side === "top" ? "marginTop" : "marginBottom"].replace("px", "");
