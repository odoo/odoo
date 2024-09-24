import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEditorTab, isTextNode, isZWS } from "@html_editor/utils/dom_info";
import { descendants, getAdjacentPreviousSiblings } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { DIRECTIONS, childNodeIndex } from "@html_editor/utils/position";

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

export class TabulationPlugin extends Plugin {
    static name = "tabulation";
    static dependencies = ["dom", "selection", "delete", "split"];
    static shared = ["indentBlocks", "outdentBlocks"];
    resources = {
        handle_tab: [],
        handle_shift_tab: [],
        handle_delete_forward: this.handleDeleteForward.bind(this),
        shortcuts: [
            { hotkey: "tab", command: "TAB" },
            { hotkey: "shift+tab", command: "SHIFT_TAB" },
        ],
        isUnsplittable: isEditorTab, // avoid merge
    };

    handleCommand(command, payload) {
        switch (command) {
            case "TAB":
                this.handleTab();
                break;
            case "SHIFT_TAB":
                this.handleShiftTab();
                break;
            case "NORMALIZE": {
                for (const tab of payload.node.querySelectorAll(".oe-tabs")) {
                    tab.setAttribute("contenteditable", "false");
                }
                this.alignTabs(payload.node);
                break;
            }
            case "CLEAN_FOR_SAVE":
                for (const tab of payload.root.querySelectorAll("span.oe-tabs")) {
                    tab.removeAttribute("contenteditable");
                }
        }
    }

    handleTab() {
        for (const callback of this.getResource("handle_tab")) {
            if (callback()) {
                return;
            }
        }

        const selection = this.shared.getEditableSelection();
        if (selection.isCollapsed) {
            this.insertTab();
        } else {
            const traversedBlocks = this.shared.getTraversedBlocks();
            this.indentBlocks(traversedBlocks);
        }
        this.dispatch("ADD_STEP");
    }

    handleShiftTab() {
        for (const callback of this.getResource("handle_shift_tab")) {
            if (callback()) {
                return;
            }
        }
        const traversedBlocks = this.shared.getTraversedBlocks();
        this.outdentBlocks(traversedBlocks);
        this.dispatch("ADD_STEP");
    }

    insertTab() {
        this.shared.domInsert(parseHTML(this.document, tabHtml));
    }

    indentBlocks(blocks) {
        const selectionToRestore = this.shared.getEditableSelection();
        const tab = parseHTML(this.document, tabHtml);
        for (const block of blocks) {
            block.prepend(tab.cloneNode(true));
        }
        this.shared.setSelection(selectionToRestore, { normalize: false });
    }

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
        const selection = this.shared.getEditableSelection();
        const { anchorNode, anchorOffset, focusNode, focusOffset } = selection;
        const updateAnchor = anchorNode === tab.nextSibling;
        const updateFocus = focusNode === tab.nextSibling;
        let zwsRemoved = 0;
        while (
            tab.nextSibling &&
            tab.nextSibling.nodeType === Node.TEXT_NODE &&
            tab.nextSibling.textContent.startsWith("\u200B")
        ) {
            this.shared.splitTextNode(tab.nextSibling, 1, DIRECTIONS.LEFT);
            tab.nextSibling.remove();
            zwsRemoved++;
        }
        if (updateAnchor || updateFocus) {
            this.shared.setSelection({
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
            range = this.shared.deleteRange({ ...range, endContainer, endOffset });
            this.shared.setSelection({
                anchorNode: range.startContainer,
                anchorOffset: range.startOffset,
            });
            return true;
        }
    }
}
