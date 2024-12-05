import { Plugin } from "../plugin";
import { isBlock, closestBlock } from "../utils/blocks";
import { fillEmpty, splitTextNode } from "../utils/dom";
import { isTextNode, isVisible } from "../utils/dom_info";
import { prepareUpdate, isFakeLineBreak } from "../utils/dom_state";
import { childNodes, closestElement, firstLeaf, lastLeaf, descendants, ancestors } from "../utils/dom_traversal";
import { DIRECTIONS, childNodeIndex, nodeSize } from "../utils/position";
import { isProtected, isProtecting } from "@html_editor/utils/dom_info";
import { isListItem } from "@html_editor/utils/list";

const isInList = (node, editable) => ancestors(node, editable).find(ancestor => isListItem(ancestor));
const isLineBreak = node => node.nodeName === "BR" && !isFakeLineBreak(node);

/**
 * @typedef { Object } SplitShared
 * @property { SplitPlugin['isUnsplittable'] } isUnsplittable
 * @property { SplitPlugin['splitAroundUntil'] } splitAroundUntil
 * @property { SplitPlugin['splitBlock'] } splitBlock
 * @property { SplitPlugin['splitBlockNode'] } splitBlockNode
 * @property { SplitPlugin['splitElement'] } splitElement
 * @property { SplitPlugin['splitElementBlock'] } splitElementBlock
 * @property { SplitPlugin['splitSelection'] } splitSelection
 */

export class SplitPlugin extends Plugin {
    static dependencies = ["selection", "history", "delete", "lineBreak"];
    static id = "split";
    static shared = [
        "splitBlock",
        "splitBlockNode",
        "splitElementBlock",
        "splitElement",
        "splitAroundUntil",
        "splitSelection",
        "isUnsplittable",
        "splitBlockSegments",
    ];
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),

        unsplittable_node_predicates: [
            // An unremovable element is also unmergeable (as merging two
            // elements results in removing one of them).
            // An unmergeable element is unsplittable and vice-versa (as
            // split and merge are reverse operations from one another).
            // Therefore, unremovable nodes are also unsplittable.
            (node) =>
                this.getResource("unremovable_node_predicates").some((predicate) =>
                    predicate(node)
                ),
            // "Unbreakable" is a legacy term that means unsplittable and
            // unmergeable.
            (node) => node.classList?.contains("oe_unbreakable"),
            (node) => ["DIV", "SECTION"].includes(node.nodeName),
        ],
    };

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------
    splitBlock() {
        this.dispatchTo("before_split_block_handlers");
        let selection = this.dependencies.selection.getEditableSelection();
        if (!selection.isCollapsed) {
            // @todo @phoenix collapseIfZWS is not tested
            // this.shared.collapseIfZWS();
            this.dependencies.delete.deleteSelection();
            selection = this.dependencies.selection.getEditableSelection();
        }

        return this.splitBlockNode({
            targetNode: selection.anchorNode,
            targetOffset: selection.anchorOffset,
        });
    }

    /**
     * @param {Object} param0
     * @param {Node} param0.targetNode
     * @param {number} param0.targetOffset
     * @returns {[HTMLElement|undefined, HTMLElement|undefined]}
     */
    splitBlockNode({ targetNode, targetOffset }) {
        if (targetNode.nodeType === Node.TEXT_NODE) {
            targetOffset = splitTextNode(targetNode, targetOffset);
            targetNode = targetNode.parentElement;
        }
        const blockToSplit = closestElement(targetNode, isBlock);
        const params = { targetNode, targetOffset, blockToSplit };

        if (this.delegateTo("split_element_block_overrides", params)) {
            return [undefined, undefined];
        }

        return this.splitElementBlock(params);
    }
    /**
     * @param {Object} param0
     * @param {HTMLElement} param0.targetNode
     * @param {number} param0.targetOffset
     * @param {HTMLElement} param0.blockToSplit
     * @returns {[HTMLElement|undefined, HTMLElement|undefined]}
     */
    splitElementBlock({ targetNode, targetOffset, blockToSplit }) {
        // If the block is unsplittable, insert a line break instead.
        if (this.isUnsplittable(blockToSplit)) {
            // @todo: t-if, t-else etc are not blocks, but they are
            // unsplittable.  The check must be done from the targetNode up to
            // the block for unsplittables. There are apparently no tests for
            // this.
            this.dependencies.lineBreak.insertLineBreakElement({ targetNode, targetOffset });
            return [undefined, undefined];
        }
        const restore = prepareUpdate(targetNode, targetOffset);

        const [beforeElement, afterElement] = this.splitElementUntil(
            targetNode,
            targetOffset,
            blockToSplit.parentElement
        );
        restore();
        const removeEmptyAndFill = (node) => {
            if (isProtecting(node) || isProtected(node)) {
                // TODO ABD: add test
                return;
            } else if (!isBlock(node) && !isVisible(node)) {
                const parent = node.parentElement;
                node.remove();
                removeEmptyAndFill(parent);
            } else {
                fillEmpty(node);
            }
        };
        removeEmptyAndFill(lastLeaf(beforeElement));
        removeEmptyAndFill(firstLeaf(afterElement));

        this.dependencies.selection.setCursorStart(afterElement);

        return [beforeElement, afterElement];
    }

    /**
     * @param {Node} node
     * @returns {boolean}
     */
    isUnsplittable(node) {
        return this.getResource("unsplittable_node_predicates").some((p) => p(node));
    }

    /**
     * Split the given element at the given offset. The element will be removed in
     * the process so caution is advised in dealing with its reference. Returns a
     * tuple containing the new elements on both sides of the split.
     *
     * @param {HTMLElement} element
     * @param {number} offset
     * @returns {[HTMLElement, HTMLElement]}
     */
    splitElement(element, offset) {
        this.dispatchTo("clean_handlers", element);
        // const before = /** @type {HTMLElement} **/ (element.cloneNode());
        /** @type {HTMLElement} **/
        const before = element.cloneNode();
        const after = /** @type {HTMLElement} **/ (element.cloneNode());
        element.before(before);
        element.after(after);
        let index = 0;
        for (const child of childNodes(element)) {
            index < offset ? before.appendChild(child) : after.appendChild(child);
            index++;
        }
        element.remove();
        return [before, after];
    }

    /**
     * Split the given element at the given offset, until the given limit ancestor.
     * The element will be removed in the process so caution is advised in dealing
     * with its reference. Returns a tuple containing the new elements on both sides
     * of the split.
     *
     * @param {HTMLElement} element
     * @param {number} offset
     * @param {HTMLElement} limitAncestor
     * @returns {[HTMLElement, HTMLElement]}
     */
    splitElementUntil(element, offset, limitAncestor) {
        if (element === limitAncestor) {
            return [element, element];
        }
        let [before, after] = this.splitElement(element, offset);
        if (after.parentElement !== limitAncestor) {
            const afterIndex = childNodeIndex(after);
            [before, after] = this.splitElementUntil(
                after.parentElement,
                afterIndex,
                limitAncestor
            );
        }
        return [before, after];
    }

    /**
     * Split around the given elements, until a given ancestor (included). Elements
     * will be removed in the process so caution is advised in dealing with their
     * references. Returns the new split root element that is a clone of
     * limitAncestor or the original limitAncestor if no split occured.
     *
     * @param {Node[] | Node} elements
     * @param {HTMLElement} limitAncestor
     * @returns { Node }
     */
    splitAroundUntil(elements, limitAncestor) {
        elements = Array.isArray(elements) ? elements : [elements];
        const firstNode = elements[0];
        const lastNode = elements[elements.length - 1];
        if ([firstNode, lastNode].includes(limitAncestor)) {
            return limitAncestor;
        }
        let before = firstNode.previousSibling;
        let after = lastNode.nextSibling;
        let beforeSplit, afterSplit;
        if (!before && !after && elements[0] !== limitAncestor) {
            return this.splitAroundUntil(elements[0].parentElement, limitAncestor);
        }
        // Split up ancestors up to font
        while (after && after.parentElement !== limitAncestor) {
            afterSplit = this.splitElement(after.parentElement, childNodeIndex(after))[0];
            after = afterSplit.nextSibling;
        }
        if (after) {
            afterSplit = this.splitElement(limitAncestor, childNodeIndex(after))[0];
            limitAncestor = afterSplit;
        }
        while (before && before.parentElement !== limitAncestor) {
            beforeSplit = this.splitElement(before.parentElement, childNodeIndex(before) + 1)[1];
            before = beforeSplit.previousSibling;
        }
        if (before) {
            beforeSplit = this.splitElement(limitAncestor, childNodeIndex(before) + 1)[1];
        }
        return beforeSplit || afterSplit || limitAncestor;
    }

    splitSelection() {
        let { startContainer, startOffset, endContainer, endOffset, direction } =
            this.dependencies.selection.getEditableSelection();
        const isInSingleContainer = startContainer === endContainer;
        if (isTextNode(endContainer) && endOffset > 0 && endOffset < nodeSize(endContainer)) {
            const endParent = endContainer.parentNode;
            const splitOffset = splitTextNode(endContainer, endOffset);
            endContainer = endParent.childNodes[splitOffset - 1] || endParent.firstChild;
            if (isInSingleContainer) {
                startContainer = endContainer;
            }
            endOffset = endContainer.textContent.length;
        }
        if (
            isTextNode(startContainer) &&
            startOffset > 0 &&
            startOffset < nodeSize(startContainer)
        ) {
            splitTextNode(startContainer, startOffset);
            startOffset = 0;
            if (isInSingleContainer) {
                endOffset = startContainer.textContent.length;
            }
        }

        const selection =
            direction === DIRECTIONS.RIGHT
                ? {
                      anchorNode: startContainer,
                      anchorOffset: startOffset,
                      focusNode: endContainer,
                      focusOffset: endOffset,
                  }
                : {
                      anchorNode: endContainer,
                      anchorOffset: endOffset,
                      focusNode: startContainer,
                      focusOffset: startOffset,
                  };
        return this.dependencies.selection.setSelection(selection, { normalize: false });
    }

    /**
     * Carefully split around a line break without creating an empty block or
     * breaking the selection.
     *
     * @private
     * @param {HTMLBRElement} br
     */
    splitAtLineBreak(br) {
        const cursors = this.dependencies.selection.preserveSelection();
        const selection = this.dependencies.selection.getEditableSelection();
        const block = closestBlock(br);
        if (block.isContentEditable) {
            const brIndex = childNodeIndex(br);
            const oldParent = br.parentElement;
            const [before, after] = this.splitElementUntil(
                br.parentElement,
                childNodeIndex(br),
                block.parentElement,
            );
            // The line break was replaced with a block break. We need to remove
            // it since it's now superfluous.
            br.remove();
            // Make sure we don't end up with an empty block on either side.
            fillEmpty(before);
            fillEmpty(after);
            // Restore the selection.
            const pointsToUpdate = [
                ["anchor", selection.anchorOffset],
                ["focus", selection.focusOffset],
            ].filter(point => selection[`${point[0]}Node`] === oldParent);
            if (pointsToUpdate.length) {
                const newSelection = { ...selection };
                for (const [side, offset] of pointsToUpdate) {
                    if (offset <= brIndex) {
                        newSelection[`${side}Node`] = before;
                        newSelection[`${side}Offset`] = 0;
                    } else {
                        newSelection[`${side}Node`] = after;
                        newSelection[`${side}Offset`] = offset - brIndex - 1;
                    }
                }
                this.dependencies.selection.setSelection(newSelection, { normalize: false });
            } else {
                cursors.restore();
            }
        }
    }
    /**
     * Find the BR that is closest to the selection point, within the same
     * block, then split around it. The selection point is
     * (startContainer, startOffset) or (endContainer, endOffset), for side
     * "start" or "end", respectively.
     *
     * @private
     * @param {"start"|"end"} side
     */
    splitEdgeLineBreak(side) {
        const selection = this.dependencies.selection.getEditableSelection();
        const selectedNodes = this.dependencies.selection.getSelectedNodes();
        const container = selection[`${side}Container`];
        const offset = selection[`${side}Offset`];
        const children = descendants(closestBlock(container));
        if (side === "end") {
            children.reverse();
        }
        // Find the index of the position of the selection point in the array.
        const selectionPointIndex = children.findIndex(child => (
            child === container ||
            selectedNodes.includes(child) ||
            (
                child.parentElement === container &&
                childNodeIndex(child) === offset
            )
        )) + (side === "start" ? 0 : 1);
        // Find the BR closest to the selection point.
        const br = children.slice(0, selectionPointIndex).findLast(isLineBreak);
        if (br && !isInList(br, this.editable)) {
            this.splitAtLineBreak(br);
        }
    }
    /**
     * Split in order to isolate any block segment in the selection. A block
     * segment forms a deliberate line in the content, separated using line
     * breaks. A line break in a list item cannot create block segments as the
     * list item visually marks its own segment (with a bullet point).
     *
     * eg: `<p>a<br>b<br>[c<br>d<br>e]<br>f<br>g</p>` marks seven line segments
     * (one per letter). The selection contains 3 line segments, which will be
     * isolated like this:
     * `<p>a<br>b</p><p>[c</p><p>d</p><p>e]</p><p>f<br>g</p>`.
     */
    splitBlockSegments() {
        // Split BR before the selection.
        this.splitEdgeLineBreak("start");
        // Split selected BRs.
        this.dependencies.selection.getSelectedNodes().filter(node => (
            isLineBreak(node) && !isInList(node, this.editable)
        )).forEach(br => this.splitAtLineBreak(br));
        // Split BR after the selection.
        this.splitEdgeLineBreak("end");
    }

    onBeforeInput(e) {
        if (e.inputType === "insertParagraph") {
            e.preventDefault();
            this.splitBlock();
            this.dependencies.history.addStep();
        }
    }
}
