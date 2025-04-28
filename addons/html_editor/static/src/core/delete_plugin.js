import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import {
    isAllowedContent,
    isButton,
    isContentEditable,
    isEmpty,
    isInPre,
    isProtected,
    isShrunkBlock,
    isTangible,
    isTextNode,
    isVisibleTextNode,
    isWhitespace,
    isZwnbsp,
    isZWS,
    nextLeaf,
    previousLeaf,
} from "../utils/dom_info";
import { getState, isFakeLineBreak, observeMutations, prepareUpdate } from "../utils/dom_state";
import {
    childNodes,
    closestElement,
    findUpTo,
    descendants,
    firstLeaf,
    getCommonAncestor,
    lastLeaf,
    findFurthest,
} from "../utils/dom_traversal";
import {
    DIRECTIONS,
    childNodeIndex,
    endPos,
    leftPos,
    nodeSize,
    rightPos,
    startPos,
} from "../utils/position";
import { CTYPES } from "../utils/content_types";
import { withSequence } from "@html_editor/utils/resource";
import { compareListTypes } from "@html_editor/main/list/utils";
import { hasTouch, isBrowserChrome, isMacOS } from "@web/core/browser/feature_detection";

/**
 * @typedef {Object} RangeLike
 * @property {Node} startContainer
 * @property {number} startOffset
 * @property {Node} endContainer
 * @property {number} endOffset
 */

/** @typedef {import("@html_editor/core/selection_plugin").EditorSelection} EditorSelection */

/**
 * @typedef {Object} DeleteShared
 * @property { DeletePlugin['delete'] } delete
 * @property { DeletePlugin['deleteRange'] } deleteRange
 * @property { DeletePlugin['deleteSelection'] } deleteSelection
 */

export class DeletePlugin extends Plugin {
    static dependencies = ["baseContainer", "selection", "history", "input", "userCommand"];
    static id = "delete";
    static shared = ["deleteBackward", "deleteForward", "deleteRange", "deleteSelection", "delete"];
    resources = {
        user_commands: [
            { id: "deleteBackward", run: () => this.delete("backward", "character") },
            { id: "deleteForward", run: () => this.delete("forward", "character") },
            { id: "deleteBackwardWord", run: () => this.delete("backward", "word") },
            { id: "deleteForwardWord", run: () => this.delete("forward", "word") },
            { id: "deleteBackwardLine", run: () => this.delete("backward", "line") },
            { id: "deleteForwardLine", run: () => this.delete("forward", "line") },
        ],
        shortcuts: [
            { hotkey: "backspace", commandId: "deleteBackward" },
            { hotkey: "delete", commandId: "deleteForward" },
            { hotkey: "control+backspace", commandId: "deleteBackwardWord" },
            { hotkey: "control+delete", commandId: "deleteForwardWord" },
            { hotkey: "control+shift+backspace", commandId: "deleteBackwardLine" },
            { hotkey: "control+shift+delete", commandId: "deleteForwardLine" },
        ],
        /** Handlers */
        beforeinput_handlers: [
            withSequence(5, this.onBeforeInputInsertText.bind(this)),
            this.onBeforeInputDelete.bind(this),
        ],
        input_handlers: (ev) => this.onAndroidChromeInput?.(ev),
        selectionchange_handlers: withSequence(5, () => this.onAndroidChromeSelectionChange?.()),
        /** Overrides */
        delete_backward_overrides: withSequence(30, this.deleteBackwardUnmergeable.bind(this)),
        delete_backward_word_overrides: withSequence(20, this.deleteBackwardUnmergeable.bind(this)),
        delete_backward_line_overrides: this.deleteBackwardUnmergeable.bind(this),
        delete_forward_overrides: withSequence(20, this.deleteForwardUnmergeable.bind(this)),
        delete_forward_word_overrides: this.deleteForwardUnmergeable.bind(this),
        delete_forward_line_overrides: this.deleteForwardUnmergeable.bind(this),

        // @todo @phoenix: move these predicates to different plugins
        unremovable_node_predicates: [
            (node) => node.classList?.contains("oe_unremovable"),
            // Monetary field
            (node) => node.matches?.("[data-oe-type='monetary'] > span"),
        ],
        invalid_for_base_container_predicates: (node) => this.isUnremovable(node, this.editable),
    };

    setup() {
        this.findPreviousPosition = this.makeFindPositionFn("backward");
        this.findNextPosition = this.makeFindPositionFn("forward");
        if (isMacOS()) {
            // Bypass the hotkey service for Alt+Backspace and Cmd+Backspace
            // on macOS which would otherwise conflict with other shortcuts.
            this.addDomListener(this.editable, "keydown", (event) => {
                const runCommand = (commandId) => {
                    this.dependencies.userCommand.getCommand(commandId).run();
                    event.stopImmediatePropagation();
                    event.preventDefault();
                };
                // Delete word backward: Option + Backspace
                if (event.altKey && event.key === "Backspace") {
                    return runCommand("deleteBackwardWord");
                }

                // Delete word forward: Option + Delete
                if (event.altKey && event.key === "Delete") {
                    return runCommand("deleteForwardWord");
                }

                // Delete line backward: Command + Backspace
                if (event.metaKey && event.key === "Backspace") {
                    return runCommand("deleteBackwardLine");
                }

                // Delete line forward: Command + Delete
                if (event.metaKey && event.key === "Delete") {
                    return runCommand("deleteForwardLine");
                }
            });
        }
    }

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------

    /**
     * @param {EditorSelection} [selection]
     */
    deleteSelection(selection = this.dependencies.selection.getEditableSelection()) {
        // @todo @phoenix: handle non-collapsed selection around a ZWS
        // see collapseIfZWS

        // Normalize selection
        selection = this.dependencies.selection.setSelection(selection);

        if (selection.isCollapsed) {
            return;
        }
        // Delete only if the targeted nodes are all editable or if every
        // non-editable node's editable ancestor is fully selected. We use the
        // targeted nodes here to be sure to include a partial text node
        // selection.
        const selectedNodes = this.dependencies.selection.getTargetedNodes();
        const canBeDeleted = (node) =>
            this.dependencies.selection.isNodeEditable(node) ||
            selectedNodes.includes(
                closestElement(node, (node) => this.dependencies.selection.isNodeEditable(node))
            );
        if (selectedNodes.some((node) => !canBeDeleted(node))) {
            return;
        }

        let range = this.adjustRange(selection, [
            this.expandRangeToIncludeNonEditables,
            this.includeEndOrStartBlock,
            this.fullyIncludeLinks,
        ]);

        if (this.delegateTo("delete_range_overrides", range)) {
            return;
        }

        range = this.deleteRange(range);
        this.setCursorFromRange(range);
    }

    /**
     * @param {"backward"|"forward"} direction
     * @param {"character"|"word"|"line"} granularity
     */
    delete(direction, granularity) {
        const selection = this.dependencies.selection.getEditableSelection();
        this.dispatchTo("before_delete_handlers");

        if (!selection.isCollapsed) {
            this.deleteSelection(selection);
        } else if (direction === "backward") {
            this.deleteBackward(selection, granularity);
        } else if (direction === "forward") {
            this.deleteForward(selection, granularity);
        } else {
            throw new Error("Invalid direction");
        }
        this.dispatchTo("delete_handlers");
        this.dependencies.history.addStep();
    }

    // --------------------------------------------------------------------------
    // Delete backward/forward
    // --------------------------------------------------------------------------

    /**
     * @param {EditorSelection} selection
     * @param {"character"|"word"|"line"} granularity
     */
    deleteBackward(selection, granularity) {
        // Normalize selection
        const { endContainer, endOffset } = this.dependencies.selection.setSelection(selection);

        let range = this.getRangeForDelete(endContainer, endOffset, "backward", granularity);

        const resourceIds = {
            character: "delete_backward_overrides",
            word: "delete_backward_word_overrides",
            line: "delete_backward_line_overrides",
        };
        if (this.delegateTo(resourceIds[granularity], range)) {
            return;
        }

        range = this.adjustRange(range, [
            this.includeEmptyInlineEnd,
            this.includePreviousZWS,
            this.includeEndOrStartBlock,
        ]);
        range = this.deleteRange(range);
        this.document.getSelection()?.removeAllRanges();
        this.setCursorFromRange(range, { collapseToEnd: true });
    }

    /**
     * @param {EditorSelection} selection
     * @param {"character"|"word"|"line"} granularity
     */
    deleteForward(selection, granularity) {
        // Normalize selection
        const { startContainer, startOffset } = this.dependencies.selection.setSelection(selection);

        let range = this.getRangeForDelete(startContainer, startOffset, "forward", granularity);

        const resourceIds = {
            character: "delete_forward_overrides",
            word: "delete_forward_word_overrides",
            line: "delete_forward_line_overrides",
        };
        if (this.delegateTo(resourceIds[granularity], range)) {
            return;
        }

        range = this.adjustRange(range, [
            this.includeEmptyInlineStart,
            this.includeNextZWS,
            this.includeEndOrStartBlock,
        ]);
        range = this.deleteRange(range);
        this.setCursorFromRange(range);
    }

    getRangeForDelete(node, offset, direction, granularity) {
        let destContainer, destOffset;
        switch (granularity) {
            case "character":
                [destContainer, destOffset] = this.findAdjacentPosition(node, offset, direction);
                break;
            case "word":
                ({ focusNode: destContainer, focusOffset: destOffset } =
                    this.dependencies.selection.modifySelection("extend", direction, "word"));
                break;
            case "line":
                [destContainer, destOffset] = this.findLineBoundary(node, offset, direction);
                break;
            default:
                throw new Error("Invalid granularity");
        }

        if (!destContainer) {
            [destContainer, destOffset] = [node, offset];
        }
        const [startContainer, startOffset, endContainer, endOffset] =
            direction === "forward"
                ? [node, offset, destContainer, destOffset]
                : [destContainer, destOffset, node, offset];

        return { startContainer, startOffset, endContainer, endOffset };
    }

    // --------------------------------------------------------------------------
    // Delete range
    // --------------------------------------------------------------------------

    /*
    Inline:
        Empty inlines get filled, no joining.
        <b>[abc]</b> -> <b>[]ZWS</b>
        <b>[abc</b> <b>d]ef</b> -> <b>[]ZWS</b> <b>ef</b>
        <b>[abc</b> <b>def]</b> -> <b>[]ZWS</b> <b>ZWS</b>
        
    Block:
        Shrunk blocks get filled.
        <p>[abc]</p> -> <p>[]<br></p>

        End block's content is appended to start block on join.
        <h1>a[bc</h1> <p>de]f</p> -> <h1>a[]f</h1>
        <h1>[abc</h1> <p>def]</p> -> <h1>[]<br></h1>

        To make left block disappear instead, use this range:
        [<h1>abc</h1> <p>de]f</p> -> []<p>f</p> (which can be normalized later, see setCursorFromRange)

    Block + Inline:
        Inline content after block is appended to block on join.
        <p>a[bc</p> d]ef -> <p>a[]ef</p>

    Inline + Block:
        Block content is unwrapped on join.
        ab[c <p>de]f</p> -> ab[]f
        ab[c <p>de]f</p> ghi -> ab[]f<br>ghi

    */

    /**
     * Removes (removable) nodes and merges block with block/inline when
     * applicable (and mergeable).
     * Returns the updated range, which is collapsed to start if the original
     * range could be completely deleted and merged.
     *
     * @param {RangeLike} range
     * @returns {RangeLike}
     */
    deleteRange(range) {
        // Do nothing if the range is collapsed.
        if (range.startContainer === range.endContainer && range.startOffset === range.endOffset) {
            return range;
        }
        // Split text nodes in order to have elements as start/end containers.
        range = this.splitTextNodes(range);

        const { startContainer, startOffset, endContainer, endOffset } = range;
        const restoreSpaces = prepareUpdate(startContainer, startOffset, endContainer, endOffset);

        let restoreFakeBRs;
        ({ restoreFakeBRs, range } = this.removeFakeBRs(range));

        // Remove nodes.
        let allNodesRemoved;
        ({ allNodesRemoved, range } = this.removeNodes(range));

        this.fillEmptyInlines(range);

        // Join fragments.
        const originalCommonAncestor = range.commonAncestorContainer;
        if (allNodesRemoved) {
            range = this.joinFragments(range);
        }

        restoreFakeBRs();
        this.fillShrunkBlocks(originalCommonAncestor);
        restoreSpaces();

        return range;
    }

    splitTextNodes({ startContainer, startOffset, endContainer, endOffset }) {
        // Splits text nodes only if necessary.
        const split = (textNode, offset) => {
            let didSplit = false;
            if (offset === 0) {
                offset = childNodeIndex(textNode);
            } else if (offset === nodeSize(textNode)) {
                offset = childNodeIndex(textNode) + 1;
            } else {
                textNode.splitText(offset);
                didSplit = true;
                offset = childNodeIndex(textNode) + 1;
            }
            return [textNode.parentElement, offset, didSplit];
        };

        if (endContainer.nodeType === Node.TEXT_NODE) {
            [endContainer, endOffset] = split(endContainer, endOffset);
        }
        if (startContainer.nodeType === Node.TEXT_NODE) {
            let didSplit;
            [startContainer, startOffset, didSplit] = split(startContainer, startOffset);
            if (startContainer === endContainer && didSplit) {
                endOffset += 1;
            }
        }

        return {
            startContainer,
            startOffset,
            endContainer,
            endOffset,
            commonAncestorContainer: getCommonAncestor(
                [startContainer, endContainer],
                this.editable
            ),
        };
    }

    // Removes fake line breaks, so that each BR left is an actual line break.
    // Returns the updated range and a function to later restore the fake BRs.
    removeFakeBRs(range) {
        let { startContainer, startOffset, endContainer, endOffset, commonAncestorContainer } =
            range;
        const visitedNodes = new Set();
        const removeBRs = (container, offset) => {
            let node = container;
            while (node !== commonAncestorContainer) {
                const lastBR = childNodes(node).findLast((child) => child.nodeName === "BR");
                if (lastBR && isFakeLineBreak(lastBR)) {
                    if (lastBR === container) {
                        [container, offset] = leftPos(lastBR);
                    } else if (node === container && offset > childNodeIndex(lastBR)) {
                        offset -= 1;
                    }
                    lastBR.remove();
                }
                visitedNodes.add(node);
                node = node.parentNode;
            }
            return [container, offset];
        };
        [startContainer, startOffset] = removeBRs(startContainer, startOffset);
        [endContainer, endOffset] = removeBRs(endContainer, endOffset);
        range = { startContainer, startOffset, endContainer, endOffset, commonAncestorContainer };

        const restoreFakeBRs = () => {
            for (const node of visitedNodes) {
                if (!node.isConnected) {
                    continue;
                }
                const lastBR = childNodes(node).findLast((child) => child.nodeName === "BR");
                if (lastBR && isFakeLineBreak(lastBR)) {
                    lastBR.after(this.document.createElement("br"));
                }
                // Shrunk blocks are restored by `fillShrunkBlocks`.
            }
        };

        return { restoreFakeBRs, range };
    }

    fillEmptyInlines(range) {
        const nodes = [range.startContainer];
        if (range.endContainer !== range.startContainer) {
            nodes.push(range.endContainer);
        }
        for (const node of nodes) {
            // @todo: mind Icons?
            // Probably need to get deepest position's element
            // @todo: update fillEmpty
            // @todo: check if nodes does not already have a ZWS/ZWNBSP
            if (!isBlock(node) && !isTangible(node)) {
                node.appendChild(this.document.createTextNode("\u200B"));
                node.setAttribute("data-oe-zws-empty-inline", "");
            }
        }
    }

    fillShrunkBlocks(commonAncestor) {
        const fillBlock = (block) => {
            if (
                block.matches("div[contenteditable='true']") &&
                !block.parentElement.isContentEditable
            ) {
                // @todo: not sure we want this when allowInlineAtRoot is true
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                baseContainer.appendChild(this.document.createElement("br"));
                block.appendChild(baseContainer);
            } else {
                block.appendChild(this.document.createElement("br"));
            }
        };
        // @todo: this ends up filling shrunk blocks outside the affected range.
        // Ideally, it should only affect the block within the boundaries of the
        // original range.
        for (const node of descendants(commonAncestor).reverse()) {
            if (isBlock(node) && isShrunkBlock(node)) {
                fillBlock(node);
            }
        }
        const containingBlock = closestBlock(commonAncestor);
        if (isShrunkBlock(containingBlock)) {
            fillBlock(containingBlock);
        }
    }

    // --------------------------------------------------------------------------
    // Remove nodes
    // --------------------------------------------------------------------------

    removeNodes(range) {
        const { startContainer, startOffset, endContainer, commonAncestorContainer } = range;
        let { endOffset } = range;
        const nodesToRemove = [];

        // Pick child nodes to the right for later removal, propagate until
        // commonAncestorContainer (non-inclusive)
        let node = startContainer;
        let startRemoveIndex = startOffset;
        while (node !== commonAncestorContainer) {
            for (let i = startRemoveIndex; i < node.childNodes.length; i++) {
                nodesToRemove.push(node.childNodes[i]);
            }
            startRemoveIndex = childNodeIndex(node) + 1;
            node = node.parentElement;
        }

        // Pick child nodes to the left for later removal, propagate until
        // commonAncestorContainer (non-inclusive)
        node = endContainer;
        let endRemoveIndex = endOffset;
        while (node !== commonAncestorContainer) {
            for (let i = 0; i < endRemoveIndex; i++) {
                nodesToRemove.push(node.childNodes[i]);
            }
            endRemoveIndex = childNodeIndex(node);
            node = node.parentElement;
        }

        // Pick commonAncestorContainer's direct children for removal
        for (let i = startRemoveIndex; i < endRemoveIndex; i++) {
            nodesToRemove.push(commonAncestorContainer.childNodes[i]);
        }

        // Remove nodes
        let allNodesRemoved = true;
        for (const node of nodesToRemove) {
            const parent = node.parentNode;
            const didRemove = this.removeNode(node);
            allNodesRemoved &&= didRemove;
            if (didRemove && endContainer === parent) {
                endOffset -= 1;
            }
        }

        const endContainerList = closestElement(endContainer, "UL, OL");
        if (
            ["OL", "UL"].includes(startContainer.nodeName) &&
            endContainerList &&
            !compareListTypes(startContainer, endContainerList)
        ) {
            const newRange = this.document.createRange();
            newRange.setStart(range.endContainer, endOffset);
            return { allNodesRemoved, range: newRange };
        }
        return { allNodesRemoved, range: { ...range, endOffset } };
    }

    // The root argument is used by some predicates in which a node is
    // conditionally unremovable (e.g. a table cell is only removable if its
    // ancestor table is also being removed).
    isUnremovable(node, root = undefined) {
        return this.getResource("unremovable_node_predicates").some((p) => p(node, root));
    }

    // Returns true if the entire subtree rooted at node was removed.
    // Unremovable nodes take the place of removable ancestors.
    removeNode(node) {
        const root = node;
        const remove = (node) => {
            let customHandling = false;
            let customIsUnremovable;
            for (const cb of this.getResource("removable_descendants_providers")) {
                const descendantsToRemove = cb(node);
                if (descendantsToRemove) {
                    for (const descendant of descendantsToRemove) {
                        remove(descendant);
                    }
                    customHandling = true;
                    customIsUnremovable = this.isUnremovable(node, root);
                    if (!customIsUnremovable) {
                        // TODO ABD: test protected + unremovable
                        node.remove();
                    }
                }
            }
            if (customHandling) {
                return !customIsUnremovable;
            }
            for (const child of [...node.childNodes]) {
                remove(child);
            }
            if (this.isUnremovable(node, root)) {
                return false;
            }
            if (node.hasChildNodes()) {
                node.before(...node.childNodes);
                node.remove();
                return false;
            }
            node.remove();
            return true;
        };
        return remove(node);
    }

    // --------------------------------------------------------------------------
    // Join
    // --------------------------------------------------------------------------

    // Joins both ends of the range if possible: block + block/inline.
    // If joined, the range is collapsed to start.
    // Returns the updated range.
    joinFragments(range) {
        const joinableLeft = this.getJoinableFragment(range, "start");
        const joinableRight = this.getJoinableFragment(range, "end");
        const join = this.getJoinOperation(joinableLeft.type, joinableRight.type);

        const didJoin = join(joinableLeft.node, joinableRight.node, range.commonAncestorContainer);

        return didJoin ? this.collapseRange(range) : range;
    }

    /**
     * Retrieves the joinable fragment based on the given range and side.
     *
     * @param {Object} range - range-like object.
     * @param {"start"|"end"} side
     * @returns {Object} - { node: Node|null, type: "block"|"inline"|"null" }
     */
    getJoinableFragment(range, side) {
        const commonAncestor = range.commonAncestorContainer;
        const container = side === "start" ? range.startContainer : range.endContainer;
        const offset = side === "start" ? range.startOffset : range.endOffset;

        if (container === range.commonAncestorContainer) {
            // This means a direct child of the commonAncestor was removed.
            // The joinable in this case is its sibling (previous for the start
            // side, next for the end side), but only if inline.
            const sibling = childNodes(commonAncestor)[side === "start" ? offset - 1 : offset];
            if (
                sibling &&
                !isBlock(sibling) &&
                !(sibling.nodeType === Node.TEXT_NODE && !isVisibleTextNode(sibling))
            ) {
                return { node: sibling, type: "inline" };
            }
            // No fragment to join.
            return { node: null, type: "null" };
        }
        // Starting from `container`, find the closest block up to
        // (not-inclusive) the common ancestor. If not found, keep the common
        // ancestor's child inline element.
        let last;
        let element = container;
        while (element !== commonAncestor) {
            if (isBlock(element)) {
                return { node: element, type: "block" };
            }
            last = element;
            element = element.parentElement;
        }
        return { node: last, type: "inline" };
    }

    getJoinOperation(leftType, rightType) {
        return (
            {
                "block + block": this.joinBlocks,
                "block + inline": this.joinInlineIntoBlock,
                "inline + block": this.joinBlockIntoInline,
            }[leftType + " + " + rightType] || (() => true)
        ).bind(this);
        // "inline + inline": Nothing to do, consider it joined.
        // Same any combination involving type "null" (no joinable element).
    }

    /**
     * An unsplittable element is also unmergeable and vice-versa (as split and
     * merge are reverse operations from one another).
     */
    isUnmergeable(node) {
        return this.getResource("unsplittable_node_predicates").some((p) => p(node));
    }

    joinBlocks(left, right, commonAncestor) {
        // Check if both blocks are mergeable.
        const canMerge = (n) => !findUpTo(n, commonAncestor, this.isUnmergeable.bind(this));
        if (!canMerge(left) || !canMerge(right)) {
            return false;
        }

        // Check if left block allows right block's content.
        const rightChildNodes = childNodes(right);
        if (!isAllowedContent(left, rightChildNodes)) {
            return false;
        }

        left.append(...rightChildNodes);
        let toRemove = right;
        let parent = right.parentElement;
        // Propagate until commonAncestor, removing empty blocks
        while (parent !== commonAncestor && parent.childNodes.length === 1) {
            toRemove = parent;
            parent = parent.parentElement;
        }
        toRemove.remove();
        return true;
    }

    joinInlineIntoBlock(leftBlock, rightInline, commonAncestor) {
        if (findUpTo(leftBlock, commonAncestor, (node) => this.isUnmergeable(node))) {
            // Left block is unmergeable.
            return false;
        }

        // @todo: avoid appending a BR as last child of the block
        while (rightInline && !isBlock(rightInline)) {
            const toAppend = rightInline;
            rightInline = rightInline.nextSibling;
            leftBlock.append(toAppend);
        }
        return true;
    }

    joinBlockIntoInline(leftInline, rightBlock, commonAncestor) {
        if (findUpTo(rightBlock, commonAncestor, (node) => this.isUnmergeable(node))) {
            // Right block is unmergeable.
            return false;
        }

        leftInline.after(...childNodes(rightBlock));
        let toRemove = rightBlock;
        let parent = rightBlock.parentElement;
        // Propagate until commonAncestor, removing empty blocks
        while (parent !== commonAncestor && parent.childNodes.length === 1) {
            toRemove = parent;
            parent = parent.parentElement;
        }
        // Restore line break between removed block and inline content after it.
        if (parent === commonAncestor) {
            const rightSibling = toRemove.nextSibling;
            if (rightSibling && !isBlock(rightSibling)) {
                rightSibling.before(this.document.createElement("br"));
            }
        }
        toRemove.remove();
        return true;
    }

    // --------------------------------------------------------------------------
    // Adjust range
    // --------------------------------------------------------------------------

    /**
     * @param {RangeLike}
     * @param {((range: Range) => Range)[]} callbacks
     * @returns {RangeLike}
     */
    adjustRange({ startContainer, startOffset, endContainer, endOffset }, callbacks) {
        let range = this.document.createRange();
        range.setStart(startContainer, startOffset);
        range.setEnd(endContainer, endOffset);

        for (const callback of callbacks) {
            range = callback.call(this, range);
        }

        ({ startContainer, startOffset, endOffset, endContainer } = range);
        return { startContainer, startOffset, endOffset, endContainer };
    }

    /**
     * <h1>[abc</h1><p>d]ef</p> -> [<h1>abc</h1><p>d]ef</p>
     *
     * @param {HTMLElement} block
     * @param {Range} range
     * @returns {Range}
     */
    includeBlockStart(block, range) {
        const { startContainer, startOffset, commonAncestorContainer } = range;
        if (
            block === commonAncestorContainer ||
            !this.isCursorAtStartOfElement(block, startContainer, startOffset)
        ) {
            return range;
        }
        range.setStartBefore(block);
        return this.includeBlockStart(block.parentNode, range);
    }

    /**
     * <p>ab[c</p><div>def]</div> ->  <p>ab[c</p><div>def</div>]
     *
     * @param {HTMLElement} block
     * @param {Range} range
     * @returns {Range}
     */
    includeBlockEnd(block, range) {
        const { startContainer, endContainer, endOffset, commonAncestorContainer } = range;
        const startList = closestElement(startContainer, "UL, OL");
        const endList = closestElement(endContainer, "UL, OL");
        if (
            block === commonAncestorContainer ||
            !this.isCursorAtEndOfElement(block, endContainer, endOffset) ||
            (startList && endList && !compareListTypes(startList, endList))
        ) {
            return range;
        }
        range.setEndAfter(block);
        return this.includeBlockEnd(block.parentNode, range);
    }

    /**
     * If range spans two blocks, try to fully include the right (end) one OR
     * the left (start) one (but not both).
     *
     * E.g.:
     * Fully includes the right block:
     * <p>ab[c</p><div>def]</div> ->  <p>ab[c</p><div>def</div>]
     * <p>[abc</p><div>def]</div> ->  <p>[abc</p><div>def</div>]
     *
     * Fully includes the left block:
     * <h1>[abc</h1><p>d]ef</p> -> [<h1>abc</h1><p>d]ef</p>
     *
     * @param {Range} range
     * @returns {Range}
     */
    includeEndOrStartBlock(range) {
        const { startContainer, endContainer, commonAncestorContainer } = range;
        const startBlock = findUpTo(startContainer, commonAncestorContainer, isBlock);
        const endBlock = findUpTo(endContainer, commonAncestorContainer, isBlock);
        if (!startBlock || !endBlock) {
            return range;
        }
        range = this.includeBlockEnd(endBlock, range);
        // Only include start block if end block could not be included.
        if (range.endContainer === endContainer) {
            range = this.includeBlockStart(startBlock, range);
        }
        return range;
    }

    /**
     * Fully select link if:
     * - range spans content inside and outside the link AND
     * - all of its content is selected.
     *
     * <a>[abc</a>d]ef -> [<a>abc</a>d]ef
     * ab[c<a>def]</a> ->  ab[c<a>def</a>]
     * But:
     * <a>[abc]</a> -> <a>[abc]</a> (remains unchanged)
     *
     * @param {Range} range
     * @returns {Range}
     */
    fullyIncludeLinks(range) {
        const { startContainer, startOffset, endContainer, endOffset, commonAncestorContainer } =
            range;
        const [startLink, endLink] = [startContainer, endContainer].map((container) =>
            findUpTo(container, commonAncestorContainer, (node) => node.nodeName === "A")
        );
        if (startLink && this.isCursorAtStartOfElement(startLink, startContainer, startOffset)) {
            range.setStartBefore(startLink);
        }
        if (endLink && this.isCursorAtEndOfElement(endLink, endContainer, endOffset)) {
            range.setEndAfter(endLink);
        }
        return range;
    }

    /**
     * @param {Range} range
     * @returns {Range}
     */
    includeEmptyInlineStart(range) {
        const element = closestElement(range.startContainer);
        if (this.isEmptyInline(element)) {
            range.setStartBefore(element);
        }
        return range;
    }

    /**
     * @param {Range} range
     * @returns {Range}
     */
    includeEmptyInlineEnd(range) {
        const element = closestElement(range.endContainer);
        if (this.isEmptyInline(element)) {
            range.setEndAfter(element);
        }
        return range;
    }

    // @todo @phoenix This is here because of the second test case in
    // delete/forward/selection collapsed/basic/should ignore ZWS, and its
    // importance is questionable.
    /**
     * @param {Range} range
     * @returns {Range}
     */
    includeNextZWS(range) {
        const { endContainer, endOffset } = range;
        if (isTextNode(endContainer) && endContainer.textContent[endOffset] === "\u200B") {
            range.setEnd(endContainer, endOffset + 1);
        }
        return range;
    }

    /**
     * @param {Range} range
     * @returns {Range}
     */
    includePreviousZWS(range) {
        const { startContainer, startOffset } = range;
        if (
            isTextNode(startContainer) &&
            startContainer.textContent[startOffset - 1] === "\u200B"
        ) {
            range.setStart(startContainer, startOffset - 1);
        }
        return range;
    }

    // Expand the range to fully include all contentEditable=False elements.
    /**
     * @param {Range} range
     * @returns {Range}
     */
    expandRangeToIncludeNonEditables(range) {
        const {
            startContainer,
            startOffset,
            endContainer,
            endOffset,
            commonAncestorContainer: commonAncestor,
        } = range;
        const isNonEditable = (node) => !isContentEditable(node);
        const startUneditable =
            startOffset === 0 &&
            !previousLeaf(startContainer, closestBlock(startContainer)) &&
            findFurthest(startContainer, commonAncestor, isNonEditable);
        if (startUneditable) {
            // @todo @phoenix: Review this spec. I suggest this instead (no block merge after removing):
            // startContainer = startUneditable.parentElement;
            // startOffset = childNodeIndex(startUneditable);
            const leaf = previousLeaf(startUneditable, this.editable);
            if (leaf) {
                range.setStart(leaf, nodeSize(leaf));
            } else {
                range.setStart(commonAncestor, 0);
            }
        }
        const endUneditable =
            endOffset === nodeSize(endContainer) &&
            !nextLeaf(endContainer, closestBlock(endContainer)) &&
            findFurthest(endContainer, commonAncestor, isNonEditable);
        if (endUneditable) {
            range.setEndAfter(endUneditable);
        }
        return range;
    }

    // --------------------------------------------------------------------------
    // Find previous/next position
    // --------------------------------------------------------------------------

    /**
     * Returns the next/previous position for deletion.
     *
     * @param {Node} node
     * @param {number} offset
     * @param {"forward"|"backward"} direction
     * @returns {[Node|null, Number|null]}
     */
    findAdjacentPosition(node, offset, direction) {
        return direction === "forward"
            ? this.findNextPosition(node, offset)
            : this.findPreviousPosition(node, offset);
    }

    /**
     *  Returns a function to find the adjacent position in the given direction.
     *
     * @param {"forward"|"backward"} direction
     */
    makeFindPositionFn(direction) {
        const isDirectionForward = direction === "forward";

        // Define helper functions based on the direction.
        // Text node helpers.
        const findVisibleChar = (
            isDirectionForward ? this.findNextVisibleChar : this.findPreviousVisibleChar
        ).bind(this);
        const charLeftPos = (index, char) => index;
        const charRightPos = (index, char) => index + char.length;
        const indexBeforeChar = isDirectionForward ? charLeftPos : charRightPos;
        const indexAfterChar = isDirectionForward ? charRightPos : charLeftPos;
        const textEdgePos = isDirectionForward ? startPos : endPos;
        // Leaf helpers.
        const adjacentLeaf = (isDirectionForward ? this.nextLeaf : this.previousLeaf).bind(this);
        const adjacentLeafFromPos = (
            isDirectionForward ? this.nextLeafFromPos : this.previousLeafFromPos
        ).bind(this);
        const beforePos = isDirectionForward ? leftPos : rightPos;
        const afterPos = isDirectionForward ? rightPos : leftPos;

        /**
         * Returns the next/previous position for deletion.
         *
         * "Before" and "after" have different meanings depending on the
         * direction: before and after mean, respectively, previous and next in
         * DOM order when direction is "forward", and the other way around when
         * direction is "backward".
         *
         * @param {Node} node
         * @param {number} offset
         * @returns {[Node|null, Number|null]}
         */
        return function findPosition(node, offset) {
            if (node.nodeType === Node.TEXT_NODE) {
                const [char, index] = findVisibleChar(node, offset);
                if (char) {
                    return [node, indexAfterChar(index, char)];
                }
            }

            // Define context: search is restricted to the closest editable root.
            const isEditableRoot = (n) => n.isContentEditable && !n.parentNode.isContentEditable;
            const editableRoot = findUpTo(node, this.editable.parentNode, isEditableRoot);

            let blockSwitch;
            const nodeClosestBlock = closestBlock(node);
            let leaf = adjacentLeafFromPos(node, offset, editableRoot);
            while (leaf) {
                blockSwitch ||= closestBlock(leaf) !== nodeClosestBlock;

                if (this.shouldSkip(leaf, blockSwitch)) {
                    leaf = adjacentLeaf(leaf, editableRoot);
                    continue;
                }

                if (leaf.nodeType === Node.TEXT_NODE) {
                    const [char, index] = findVisibleChar(...textEdgePos(leaf));
                    if (char) {
                        const idx = (blockSwitch ? indexBeforeChar : indexAfterChar)(index, char);
                        return [leaf, idx];
                    }
                } else if (!leaf.isContentEditable && isBlock(leaf)) {
                    // E.g. Desired range for deleteForward:
                    // <p>abc[</p><div contenteditable="false">def</div>]<p>ghi</p>
                    return afterPos(leaf);
                } else {
                    return blockSwitch ? beforePos(leaf) : afterPos(leaf);
                }
                leaf = adjacentLeaf(leaf, editableRoot);
            }
            return [null, null];
        };
    }

    findLineBoundary(container, offset, direction) {
        const adjacentLeaf = direction === "forward" ? nextLeaf : previousLeaf;
        const edgeIndex = (node) => (direction === "forward" ? nodeSize(node) : 0);
        const block = closestBlock(container);
        let last = container;
        let node = adjacentLeaf(container, this.editable);
        // look for a BR or a block start
        while (node && node.nodeName !== "BR" && closestBlock(node) === block) {
            last = node;
            node = adjacentLeaf(node, this.editable);
        }
        if (last === container && offset === edgeIndex(container)) {
            // Cursor is already next to the line break, go to following position.
            return this.findAdjacentPosition(container, offset, direction);
        }
        return direction === "forward" ? rightPos(last) : leftPos(last);
    }

    // @todo @phoenix: there are not enough tests for visibility of characters
    // (invisible whitespace, separate nodes, etc.)
    isVisibleChar(char, textNode, offset) {
        // Protected nodes are always "visible" for the editor
        if (isProtected(textNode)) {
            // TODO ABD: add test
            return true;
        }
        const isZwnbspLinkPad = (node) =>
            isButton(node.previousSibling) || isButton(node.nextSibling);
        if (isZwnbsp(textNode) && isZwnbspLinkPad(textNode)) {
            return true;
        }
        // ZWS and ZWNBSP are invisible.
        if (["\u200B", "\uFEFF"].includes(char)) {
            return false;
        }
        if (!isWhitespace(char) || isInPre(textNode)) {
            return true;
        }

        // Assess visibility of whitespace.
        // Whitespace is visible if it's immediately preceded by content, and
        // followed by content before a BR or block start/end.

        // If not preceded by content, it is invisible.
        if (offset) {
            return !isWhitespace(textNode.textContent[offset - char.length]);
        } else if (!(getState(...leftPos(textNode), DIRECTIONS.LEFT).cType & CTYPES.CONTENT)) {
            return false;
        }

        // Space is only visible if it's followed by content (with an optional
        // sequence of invisible spaces in between), before a BR or block
        // end/start.
        const charsToTheRight = textNode.textContent.slice(offset + char.length);
        for (char of charsToTheRight) {
            if (!isWhitespace(char)) {
                return true;
            }
        }
        // No content found in text node, look to the right of it
        if (getState(...rightPos(textNode), DIRECTIONS.RIGHT).cType & CTYPES.CONTENT) {
            return true;
        }

        return false;
    }

    shouldSkip(leaf, blockSwitch) {
        if (leaf.nodeType === Node.TEXT_NODE) {
            return false;
        }
        // @todo Maybe skip anything that is not an element (e.g. comment nodes)
        if (blockSwitch) {
            return false;
        }
        if (leaf.nodeName === "BR" && isFakeLineBreak(leaf)) {
            return true;
        }
        if (
            this.getResource("functional_empty_node_predicates").some((predicate) =>
                predicate(leaf)
            )
        ) {
            return false;
        }
        if (isEmpty(leaf) || isZWS(leaf)) {
            return true;
        }
        return false;
    }

    findPreviousVisibleChar(textNode, index) {
        // @todo @phoenix: write tests for chars with size > 1 (emoji, etc.)
        // Use the string iterator to handle surrogate pairs.
        const chars = [...textNode.textContent.slice(0, index)];
        let char = chars.pop();
        while (char) {
            index -= char.length;
            if (this.isVisibleChar(char, textNode, index)) {
                return [char, index];
            }
            char = chars.pop();
        }
        return [null, null];
    }

    findNextVisibleChar(textNode, index) {
        // Use the string iterator to handle surrogate pairs.
        for (const char of textNode.textContent.slice(index)) {
            if (this.isVisibleChar(char, textNode, index)) {
                return [char, index];
            }
            index += char.length;
        }
        return [null, null];
    }

    // If leaf is part of a contenteditable=false tree, consider its root as the
    // leaf instead.
    adjustedLeaf(leaf, refEditableRoot) {
        const isNonEditable = (node) => !isContentEditable(node);
        const nonEditableRoot = leaf && findFurthest(leaf, refEditableRoot, isNonEditable);
        return nonEditableRoot || leaf;
    }

    previousLeaf(node, editableRoot) {
        return this.adjustedLeaf(previousLeaf(node, editableRoot), editableRoot);
    }

    nextLeaf(node, editableRoot) {
        return this.adjustedLeaf(nextLeaf(node, editableRoot), editableRoot);
    }

    previousLeafFromPos(node, offset, editableRoot) {
        const leaf =
            node.hasChildNodes() && offset > 0
                ? lastLeaf(node.childNodes[offset - 1])
                : previousLeaf(node, editableRoot);
        return this.adjustedLeaf(leaf, editableRoot);
    }

    nextLeafFromPos(node, offset, editableRoot) {
        const leaf =
            node.hasChildNodes() && offset < nodeSize(node)
                ? firstLeaf(node.childNodes[offset])
                : nextLeaf(node, editableRoot);
        return this.adjustedLeaf(leaf, editableRoot);
    }

    // --------------------------------------------------------------------------
    // Event handlers
    // --------------------------------------------------------------------------

    onBeforeInputDelete(ev) {
        const handledInputTypes = {
            deleteContentBackward: ["backward", "character"],
            deleteContentForward: ["forward", "character"],
            deleteWordBackward: ["backward", "word"],
            deleteWordForward: ["forward", "word"],
            deleteHardLineBackward: ["backward", "line"],
            deleteHardLineForward: ["forward", "line"],
        };
        const argsForDelete = handledInputTypes[ev.inputType];
        if (argsForDelete) {
            this.delete(...argsForDelete);
            ev.preventDefault();
            if (isBrowserChrome() && hasTouch()) {
                this.preventDefaultDeleteAndroidChrome(ev);
            }
        }
    }

    onBeforeInputInsertText(ev) {
        if (ev.inputType === "insertText") {
            const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
            if (!selection.isCollapsed) {
                this.dispatchTo("before_delete_handlers");
                this.deleteSelection(selection);
                this.dispatchTo("delete_handlers");
            }
            // Default behavior: insert text and trigger input event
        }
    }

    /**
     * Beforeinput event of type deleteContentBackward cannot be default
     * prevented in Android Chrome. So we need to revert:
     * - eventual mutations between beforeinput and input events
     * - eventual selection change after input event
     *
     * @param {InputEvent} beforeInputEvent
     */
    preventDefaultDeleteAndroidChrome(beforeInputEvent) {
        const restoreDOM = this.dependencies.history.makeSavePoint();
        this.onAndroidChromeInput = (ev) => {
            if (ev.inputType !== beforeInputEvent.inputType) {
                return;
            }
            // Revert DOM changes that occurred between beforeinput and input.
            restoreDOM();

            // Revert selection changes after input event, within the same tick.
            // If further mutations occurred, consider selection change legit
            // (e.g. dictionary input) and do not revert it.
            const { restore: restoreSelection } = this.dependencies.selection.preserveSelection();
            const observerOptions = { childList: true, subtree: true, characterData: true };
            const getMutationRecords = observeMutations(this.editable, observerOptions);
            this.onAndroidChromeSelectionChange = () => {
                const shouldRevertSelectionChanges = !getMutationRecords().length;
                if (shouldRevertSelectionChanges) {
                    restoreSelection();
                }
            };
            setTimeout(() => delete this.onAndroidChromeSelectionChange);
        };
    }

    // ======== AD-HOC STUFF ========

    deleteBackwardUnmergeable(range) {
        const { startContainer, startOffset, endContainer, endOffset } = range;
        return this.deleteCharUnmergeable(endContainer, endOffset, startContainer, startOffset);
    }

    // @todo @phoenix: write tests for this
    deleteForwardUnmergeable(range) {
        const { startContainer, startOffset, endContainer, endOffset } = range;
        return this.deleteCharUnmergeable(startContainer, startOffset, endContainer, endOffset);
    }

    // Trap cursor inside unmergeable element. Remove it if empty.
    deleteCharUnmergeable(sourceContainer, sourceOffset, destContainer, destOffset) {
        if (!destContainer) {
            return;
        }
        const commonAncestor = getCommonAncestor([sourceContainer, destContainer], this.editable);
        const closestUnmergeable = findUpTo(sourceContainer, commonAncestor, (node) =>
            this.isUnmergeable(node)
        );
        if (!closestUnmergeable) {
            return;
        }

        if (
            (isEmpty(closestUnmergeable) ||
                this.delegateTo("is_empty_predicates", closestUnmergeable)) &&
            !this.isUnremovable(closestUnmergeable)
        ) {
            closestUnmergeable.remove();
            this.dependencies.selection.setSelection({
                anchorNode: destContainer,
                anchorOffset: destOffset,
            });
        } else {
            this.dependencies.selection.setSelection({
                anchorNode: sourceContainer,
                anchorOffset: sourceOffset,
            });
        }
        return true;
    }

    // --------------------------------------------------------------------------
    // utils
    // --------------------------------------------------------------------------

    isEmptyInline(element) {
        if (isBlock(element)) {
            return false;
        }
        if (isZWS(element)) {
            return true;
        }
        return element.innerHTML.trim() === "";
    }

    isCursorAtStartOfElement(element, cursorNode, cursorOffset) {
        const [node] = this.findPreviousPosition(cursorNode, cursorOffset);
        return !element.contains(node);
    }

    isCursorAtEndOfElement(element, cursorNode, cursorOffset) {
        const [node] = this.findNextPosition(cursorNode, cursorOffset);
        return !element.contains(node);
    }

    /**
     * @param {RangeLike} range
     */
    setCursorFromRange(range, { collapseToEnd = false } = {}) {
        range = this.collapseRange(range, { toEnd: collapseToEnd });
        const [anchorNode, anchorOffset] = this.normalizeEnterBlock(
            range.startContainer,
            range.startOffset
        );
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
    }

    // @todo: no need for this once selection in the editable root is corrected?
    normalizeEnterBlock(node, offset) {
        while (isBlock(node.childNodes[offset])) {
            [node, offset] = [node.childNodes[offset], 0];
        }
        return [node, offset];
    }

    /**
     * @param {RangeLike} range
     */
    collapseRange(range, { toEnd = false } = {}) {
        let { startContainer, startOffset, endContainer, endOffset } = range;
        if (toEnd) {
            [startContainer, startOffset] = [endContainer, endOffset];
        } else {
            [endContainer, endOffset] = [startContainer, startOffset];
        }
        const commonAncestorContainer = startContainer;
        return { startContainer, startOffset, endContainer, endOffset, commonAncestorContainer };
    }
}
