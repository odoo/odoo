import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { splitTextNode } from "@html_editor/utils/dom";
import { isEditorTab, isTextNode, isZWS } from "@html_editor/utils/dom_info";
import {
    descendants,
    getAdjacentPreviousSiblings,
    closestElement,
    firstLeaf,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { DIRECTIONS, childNodeIndex } from "@html_editor/utils/position";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

const tabHtml = '<span class="oe-tabs" contenteditable="false">\u0009</span>\u200B';
const GRID_COLUMN_WIDTH = 40; //@todo Configurable?

/**
 * Checks if the given tab element represents an indentation.
 * An indentation tab is one that is not preceded by visible text.
 *
 * @param {HTMLElement} tab - The tab element to check.
 * @returns {boolean} - True if the tab represents an indentation, false otherwise.
 */
function isIndentationTab(tab) {
    return !getAdjacentPreviousSiblings(tab).some(
        (sibling) => isTextNode(sibling) && !/^[\u200B\s]*$/.test(sibling.textContent)
    );
}

/**
 * @typedef { Object } TabulationShared
 * @property { TabulationPlugin['indentBlocks'] } indentBlocks
 * @property { TabulationPlugin['outdentBlocks'] } outdentBlocks
 */

export class TabulationPlugin extends Plugin {
    static id = "tabulation";
    static dependencies = ["dom", "selection", "history", "delete"];
    static shared = ["indentBlocks", "outdentBlocks"];
    resources = {
        user_commands: [
            {
                id: "tab",
                run: this.handleTab.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "shiftTab",
                run: this.handleShiftTab.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        shortcuts: [
            { hotkey: "tab", commandId: "tab" },
            { hotkey: "shift+tab", commandId: "shiftTab" },
        ],
        content_not_editable_providers: (rootEl) => [...selectElements(rootEl, ".oe-tabs")],
        contenteditable_to_remove_selector: "span.oe-tabs",

        /** Handlers */
        normalize_handlers: this.normalize.bind(this),

        /** Overrides */
        delete_forward_overrides: this.handleDeleteForward.bind(this),

        unsplittable_node_predicates: isEditorTab, // avoid merge
    };

    handleTab() {
        if (this.delegateTo("tab_overrides")) {
            return;
        }

        const selection = this.dependencies.selection.getEditableSelection();
        if (selection.isCollapsed) {
            this.insertTab();
        } else {
            const targetedBlocks = this.dependencies.selection.getTargetedBlocks();
            this.indentBlocks(targetedBlocks);
        }
        this.dependencies.history.addStep();
    }

    handleShiftTab() {
        if (this.delegateTo("shift_tab_overrides")) {
            return;
        }
        const targetedBlocks = this.dependencies.selection.getTargetedBlocks();
        this.outdentBlocks(targetedBlocks);
        this.dependencies.history.addStep();
    }

    insertTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const element = closestElement(selection.anchorNode);
        const isSelectionAtStart =
            firstLeaf(element) === selection.anchorNode &&
            (selection.anchorOffset === 0 || element.textContent === "\u200B");
        const tab = parseHTML(this.document, tabHtml);
        if (isSelectionAtStart && !isBlock(element)) {
            element.before(tab);
        } else {
            this.dependencies.dom.insert(tab);
        }
    }

    /**
     * @param {HTMLElement} blocks
     */
    indentBlocks(blocks) {
        const selectionToRestore = this.dependencies.selection.getEditableSelection();
        const tab = parseHTML(this.document, tabHtml);
        for (const block of blocks) {
            block.prepend(tab.cloneNode(true));
        }
        this.dependencies.selection.setSelection(selectionToRestore, { normalize: false });
    }

    /**
     * @param {HTMLElement} blocks
     */
    outdentBlocks(blocks) {
        for (const block of blocks) {
            const firstTab = descendants(block).find(isEditorTab);
            if (firstTab && isIndentationTab(firstTab)) {
                this.removeTrailingZWS(firstTab);
                firstTab.remove();
            }
        }
    }

    removeTrailingZWS(tab) {
        const selection = this.dependencies.selection.getEditableSelection();
        const { anchorNode, anchorOffset, focusNode, focusOffset } = selection;
        const updateAnchor = anchorNode === tab.nextSibling;
        const updateFocus = focusNode === tab.nextSibling;
        let zwsRemoved = 0;
        while (
            tab.nextSibling &&
            tab.nextSibling.nodeType === Node.TEXT_NODE &&
            tab.nextSibling.textContent.startsWith("\u200B")
        ) {
            splitTextNode(tab.nextSibling, 1, DIRECTIONS.LEFT);
            tab.nextSibling.remove();
            zwsRemoved++;
        }
        if (updateAnchor || updateFocus) {
            this.dependencies.selection.setSelection({
                anchorNode: updateAnchor ? tab.nextSibling : anchorNode,
                anchorOffset: updateAnchor ? Math.max(0, anchorOffset - zwsRemoved) : anchorOffset,
                focusNode: updateFocus ? tab.nextSibling : focusNode,
                focusOffset: updateFocus ? Math.max(0, focusOffset - zwsRemoved) : focusOffset,
            });
        }
    }

    /**
     * @param {HTMLSpanElement} tabSpan - span.oe-tabs element
     */
    adjustTabWidth(tabSpan) {
        let tabPreviousSibling = tabSpan.previousSibling;
        while (isZWS(tabPreviousSibling)) {
            tabPreviousSibling = tabPreviousSibling.previousSibling;
        }
        if (isEditorTab(tabPreviousSibling)) {
            tabSpan.style.width = `${GRID_COLUMN_WIDTH}px`;
            return;
        }
        const spanRect = tabSpan.getBoundingClientRect();
        const referenceRect = this.editable.firstElementChild?.getBoundingClientRect();
        // @ todo @phoenix Re-evaluate if this check is necessary.
        // Values from getBoundingClientRect() are all zeros during
        // Editor startup or saving. We cannot recalculate the tabs
        // width in thoses cases.
        if (!referenceRect?.width || !spanRect.width) {
            return;
        }
        const relativePosition = spanRect.left - referenceRect.left;
        const distToNextGridLine = GRID_COLUMN_WIDTH - (relativePosition % GRID_COLUMN_WIDTH);
        // Round to the first decimal point.
        const width = distToNextGridLine.toFixed(1);
        tabSpan.style.width = `${width}px`;
    }

    /**
     * Aligns the tabs under the specified tree to a grid.
     *
     * @param {HTMLElement} [root] - The tree root.
     */
    alignTabs(root = this.editable) {
        const block = closestBlock(root);
        if (!block) {
            return;
        }
        for (const tab of block.querySelectorAll("span.oe-tabs")) {
            this.adjustTabWidth(tab);
        }
    }

    // When deleting an editor tab, we need to ensure it's related
    // ZWS will deleted as well.
    // @todo @phoenix: for some reason, there might be more than one ZWS.
    // Investigate why.
    expandRangeToIncludeZWS(tabElement) {
        let previous = tabElement;
        let node = tabElement.nextSibling;
        while (node?.nodeType === Node.TEXT_NODE) {
            for (let i = 0; i < node.textContent.length; i++) {
                if (node.textContent[i] !== "\u200B") {
                    return [node, i];
                }
            }
            previous = node;
            node = node.nextSibling;
        }
        return [previous.parentElement, childNodeIndex(previous) + 1];
    }

    // @todo consider registering this as adjustRange callback instead.
    handleDeleteForward(range) {
        let { endContainer, endOffset } = range;
        if (!(endContainer?.nodeType === Node.ELEMENT_NODE) || !endOffset) {
            return;
        }
        const nodeToDelete = endContainer.childNodes[endOffset - 1];
        if (isEditorTab(nodeToDelete)) {
            [endContainer, endOffset] = this.expandRangeToIncludeZWS(nodeToDelete);
            range = this.dependencies.delete.deleteRange({ ...range, endContainer, endOffset });
            this.dependencies.selection.setSelection({
                anchorNode: range.startContainer,
                anchorOffset: range.startOffset,
            });
            return true;
        }
    }
    normalize(el) {
        this.alignTabs(el);
    }
}
