import { isListItem } from "@html_editor/main/list/utils";
import { Plugin } from "../plugin";
import { isBlock, closestBlock } from "../utils/blocks";
import { fillEmpty, splitTextNode } from "../utils/dom";
import {
    allowsParagraphRelatedElements,
    isContentEditable,
    isContentEditableAncestor,
    isPhrasingContent,
    isTextNode,
    isVisible,
} from "../utils/dom_info";
import { prepareUpdate, isFakeLineBreak } from "../utils/dom_state";
import {
    childNodes,
    closestElement,
    firstLeaf,
    lastLeaf,
    ancestors,
    createDOMPathGenerator,
} from "../utils/dom_traversal";
import { DIRECTIONS, childNodeIndex, nodeSize } from "../utils/position";
import { isProtected, isProtecting } from "@html_editor/utils/dom_info";

const isInList = (node, editable) =>
    ancestors(node, editable).find((ancestor) => isListItem(ancestor));
const isLineBreak = (node) => node.nodeName === "BR" && !isFakeLineBreak(node);
const [getPreviousLeavesInBlock, getNextLeavesInBlock] = [DIRECTIONS.LEFT, DIRECTIONS.RIGHT]
    .map((direction) =>
        createDOMPathGenerator(direction, {
            leafOnly: true,
            stopTraverseFunction: isBlock,
            stopFunction: isBlock,
        })
    )
    .map((path) => (node, offset) => [...path(node, offset)]);

/**
 * @typedef { Object } SplitShared
 * @property { SplitPlugin['isUnsplittable'] } isUnsplittable
 * @property { SplitPlugin['splitAroundUntil'] } splitAroundUntil
 * @property { SplitPlugin['splitBlock'] } splitBlock
 * @property { SplitPlugin['splitBlockNode'] } splitBlockNode
 * @property { SplitPlugin['splitElement'] } splitElement
 * @property { SplitPlugin['splitElementBlock'] } splitElementBlock
 * @property { SplitPlugin['splitSelection'] } splitSelection
 * @property { SplitPlugin['splitBlockSegments'] } splitBlockSegments
 */

/**
 * @typedef {(({element: HTMLElement, secondPart: HTMLElement}) => void)[]} after_split_element_handlers
 * @typedef {(() => void)[]} before_split_block_handlers
 *
 * @typedef {((params: { targetNode: Node, targetOffset: number, blockToSplit: HTMLElement | null }) => void | true)[]} split_element_block_overrides
 *
 * @typedef {((node: Node) => boolean)[]} unsplittable_node_predicates
 */

export class SplitPlugin extends Plugin {
    static dependencies = ["baseContainer", "selection", "history", "input", "delete", "lineBreak"];
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
    /** @type {import("plugins").EditorResources} */
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),

        unsplittable_node_predicates: [
            // An unremovable element is also unmergeable (as merging two
            // elements results in removing one of them).
            // An unmergeable element is unsplittable and vice-versa (as
            // split and merge are reverse operations from one another).
            // Therefore, unremovable nodes are also unsplittable.
            (node) => this.dependencies.delete.isUnremovable(node),
            // "Unbreakable" is a legacy term that means unsplittable and
            // unmergeable.
            (node) => node.classList?.contains("oe_unbreakable"),
            (node) => {
                const isExplicitlyNotContentEditable = (node) =>
                    // In the `contenteditable` attribute consideration,
                    // disconnected nodes can be unsplittable only if they are
                    // explicitly set under a contenteditable="false" element.
                    !isContentEditable(node) &&
                    (node.isConnected || closestElement(node, "[contenteditable]"));
                return (
                    isExplicitlyNotContentEditable(node) ||
                    // If node sets contenteditable='true' and is inside a non-editable
                    // context, it has to be unsplittable since splitting it would modify
                    // the non-editable parent content.
                    (node.parentElement &&
                        isContentEditableAncestor(node) &&
                        isExplicitlyNotContentEditable(node.parentElement))
                );
            },
            (node) => node.nodeName === "SECTION",
        ],
        selection_blocker_predicates: (blocker) => {
            if (this.isUnsplittable(blocker)) {
                return true;
            }
        },
    };

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------
    splitBlock() {
        this.dispatchTo("before_split_block_handlers");
        let selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
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
        const fillEmptyElement = (node) => {
            if (isProtecting(node) || isProtected(node)) {
                // TODO ABD: add test
                return;
            } else if (node.nodeType === Node.TEXT_NODE && !isVisible(node)) {
                const parent = node.parentElement;
                node.remove();
                fillEmptyElement(parent);
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.hasAttribute("data-oe-zws-empty-inline")) {
                    delete node.dataset.oeZwsEmptyInline;
                }
                fillEmpty(node);
            }
        };
        fillEmptyElement(lastLeaf(beforeElement));
        fillEmptyElement(firstLeaf(afterElement));

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
     * Split the given element at the given offset. Returns a tuple containing
     * the new elements on both sides of the split.
     *
     * @param {HTMLElement} element
     * @param {number} offset
     * @returns {[HTMLElement, HTMLElement]}
     */
    splitElement(element, offset) {
        /** @type {HTMLElement} **/
        const secondPart = element.cloneNode();
        const children = childNodes(element);
        secondPart.append(...children.slice(offset));
        element.after(secondPart);
        this.dispatchTo("after_split_element_handlers", { element, secondPart });
        return [element, secondPart];
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
        this.dispatchTo("before_split_around_until_handlers", limitAncestor);
        elements = Array.isArray(elements) ? elements : [elements];
        const firstNode = elements[0];
        const lastNode = elements[elements.length - 1];
        if ([firstNode, lastNode].includes(limitAncestor)) {
            return limitAncestor;
        }
        let before = firstNode.previousSibling;
        let after = lastNode.nextSibling;
        let beforeSplit, afterSplit;
        if (
            !before &&
            !after &&
            firstNode.parentElement !== limitAncestor &&
            lastNode.parentElement !== limitAncestor
        ) {
            return this.splitAroundUntil(
                [firstNode.parentElement, lastNode.parentElement],
                limitAncestor
            );
        } else if (!after && lastNode.parentElement !== limitAncestor) {
            return this.splitAroundUntil([firstNode, lastNode.parentElement], limitAncestor);
        } else if (!before && firstNode.parentElement !== limitAncestor) {
            return this.splitAroundUntil([firstNode.parentElement, lastNode], limitAncestor);
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
        const { setSelection, getEditableSelection } = this.dependencies.selection;
        const { startContainer, startOffset, endContainer, endOffset } = getEditableSelection();

        const brs = [
            // BR before the selection:
            getPreviousLeavesInBlock(startContainer, startOffset).find(isLineBreak),
            // Selected BRs:
            ...this.dependencies.selection.getTargetedNodes(),
            // BR after the selection:
            getNextLeavesInBlock(endContainer, endOffset).find(isLineBreak),
        ].filter((node) => node && isLineBreak(node) && !isInList(node, this.editable));
        for (const br of brs) {
            let block = closestBlock(br);
            if (!block?.isContentEditable) {
                continue;
            }

            // Check if we can split at this line break.
            const unsplittable = ancestors(br, block).find(this.isUnsplittable.bind(this));
            const canWrapInUnsplittable = allowsParagraphRelatedElements(unsplittable);
            if (unsplittable) {
                if (canWrapInUnsplittable) {
                    // If splitting here would split an unsplittable element,
                    // remove the line break and wrap the content around it in
                    // new base containers.
                    const cursors = this.dependencies.selection.preserveSelection();
                    const children = [...unsplittable.childNodes];
                    const brIndex = childNodeIndex(br);
                    // Wrap only until the first node that can't be wrapped, in
                    // both directions.
                    const isInvalid = (node) => !isPhrasingContent(node);
                    const startInvalid = children.slice(0, brIndex).findLast(isInvalid);
                    const endInvalid = children.slice(brIndex + 1).find(isInvalid);
                    const childrenToInsert = children.slice(
                        startInvalid ? childNodeIndex(startInvalid) + 1 : 0,
                        endInvalid ? childNodeIndex(endInvalid) : children.length
                    );
                    // The new base container will become the new block parent
                    // of the BR.
                    block = this.dependencies.baseContainer.createBaseContainer();
                    childrenToInsert[0]?.before(block);
                    block.append(...childrenToInsert);
                    cursors.restore();
                } else {
                    // If we can't insert a base container here, there's nothing
                    // we can do.
                    continue;
                }
            }

            // Now let's split at the line break.
            const cursors = this.dependencies.selection.preserveSelection();
            let { anchorNode, anchorOffset, focusNode, focusOffset } = getEditableSelection();
            const brIndex = childNodeIndex(br);
            const oldParent = br.parentElement;
            const [before, after] = this.splitElementUntil(oldParent, brIndex, block.parentElement);
            br.remove();
            [before, after].forEach(fillEmpty);

            // Restore the selection.
            if ([anchorNode, focusNode].some((node) => node === oldParent)) {
                // We can't use `cursors.remapNode` here because the old parent
                // was split into two new nodes.
                // eg, `<p>[a<br>b]</p>` with selection (p, 0, p, 3) ->
                // `<p>[a</p><p>b]</p>` -> anchor p !== focus p.
                const remapPos = (i) => (i <= brIndex ? [before, 0] : [after, i - brIndex - 1]);
                [[anchorNode, anchorOffset], [focusNode, focusOffset]] = [
                    [anchorNode, anchorOffset],
                    [focusNode, focusOffset],
                ].map(([node, offset]) => (node === oldParent ? remapPos(offset) : [node, offset]));
                setSelection(
                    { anchorNode, anchorOffset, focusNode, focusOffset },
                    { normalize: false }
                );
            } else {
                cursors.restore();
            }
        }
    }

    onBeforeInput(e) {
        if (e.inputType === "insertParagraph") {
            e.preventDefault();
            this.splitBlock();
            this.dependencies.history.addStep();
        }
    }
}
