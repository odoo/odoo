import { Plugin } from "../plugin";
import { isBlock } from "../utils/blocks";
import { fillEmpty, splitTextNode } from "../utils/dom";
import {
    isContentEditable,
    isContentEditableAncestor,
    isTextNode,
    isVisible,
} from "../utils/dom_info";
import { prepareUpdate } from "../utils/dom_state";
import { childNodes, closestElement, firstLeaf, lastLeaf, findUpTo } from "../utils/dom_traversal";
import { DIRECTIONS, childNodeIndex, nodeSize } from "../utils/position";
import { isProtected, isProtecting } from "@html_editor/utils/dom_info";

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
            (node) =>
                this.getResource("unremovable_node_predicates").some((predicate) =>
                    predicate(node)
                ),
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
        } else if (!closestElement(selection.anchorNode).isContentEditable) {
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
        // If the block is unsplittable or the targetNode is within an
        // unsplittable element, insert a line break instead.
        if (
            this.isUnsplittable(blockToSplit) ||
            findUpTo(targetNode, blockToSplit, (el) => this.isUnsplittable(el))
        ) {
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
     * Split the given element at the given offset. The element will be removed in
     * the process so caution is advised in dealing with its reference. Returns a
     * tuple containing the new elements on both sides of the split.
     *
     * @param {HTMLElement} element
     * @param {number} offset
     * @returns {[HTMLElement, HTMLElement]}
     */
    splitElement(element, offset) {
        /** @type {HTMLElement} **/
        const firstPart = element.cloneNode();
        /** @type {HTMLElement} **/
        const secondPart = element.cloneNode();
        element.before(firstPart);
        element.after(secondPart);
        const children = childNodes(element);
        firstPart.append(...children.slice(0, offset));
        secondPart.append(...children.slice(offset));
        element.remove();
        this.dispatchTo("after_split_element_handlers", { firstPart, secondPart });
        return [firstPart, secondPart];
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

    onBeforeInput(e) {
        if (e.inputType === "insertParagraph") {
            e.preventDefault();
            this.splitBlock();
            this.dependencies.history.addStep();
        }
    }
}
