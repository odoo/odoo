import { Plugin } from "../plugin";
import { isBlock } from "../utils/blocks";
import { fillEmpty } from "../utils/dom";
import { isVisible } from "../utils/dom_info";
import { prepareUpdate } from "../utils/dom_state";
import { closestElement, firstLeaf, lastLeaf } from "../utils/dom_traversal";
import { DIRECTIONS, childNodeIndex } from "../utils/position";

export class SplitPlugin extends Plugin {
    static dependencies = ["selection"];
    static name = "split";
    static shared = [
        "splitBlock",
        "splitElementBlock",
        "splitElement",
        "splitAroundUntil",
        "splitTextNode",
        "splitSelection",
    ];

    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput.bind(this));
    }
    handleCommand(command, payload) {
        switch (command) {
            case "SPLIT_BLOCK":
                this._splitBlock();
                break;
            case "SPLIT_BLOCK_NODE":
                this.splitBlockNode(payload);
                break;
        }
    }

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------
    splitBlock() {
        let selection = this.shared.getEditableSelection();
        if (!selection.isCollapsed) {
            // @todo @phoenix collapseIfZWS is not tested
            // this.shared.collapseIfZWS();
            this.dispatch("DELETE_SELECTION");
            selection = this.shared.getEditableSelection();
        }

        return this.splitBlockNode({
            targetNode: selection.anchorNode,
            targetOffset: selection.anchorOffset,
        });
    }
    _splitBlock() {
        this.splitBlock();
        this.dispatch("ADD_STEP");
    }

    /**
     * @param {Object} param0
     * @param {Node} param0.targetNode
     * @param {number} param0.targetOffset
     * @returns {[HTMLElement|undefined, HTMLElement|undefined]}
     */
    splitBlockNode({ targetNode, targetOffset }) {
        if (targetNode.nodeType === Node.TEXT_NODE) {
            targetOffset = this.splitTextNode(targetNode, targetOffset);
            targetNode = targetNode.parentElement;
        }
        const blockToSplit = closestElement(targetNode, isBlock);

        for (const { callback } of this.resources["split_element_block"]) {
            if (callback({ targetNode, targetOffset, blockToSplit })) {
                return [undefined, undefined];
            }
        }

        return this.splitElementBlock({ targetNode, targetOffset, blockToSplit });
    }
    /**
     * @param {Object} param0
     * @param {HTMLElement} param0.targetNode
     * @param {number} param0.targetOffset
     * @param {HTMLElement} param0.blockToSplit
     * @returns {[HTMLElement|undefined, HTMLElement|undefined]}
     */
    splitElementBlock({ targetNode, targetOffset, blockToSplit }) {
        const restore = prepareUpdate(targetNode, targetOffset);

        const [beforeElement, afterElement] = this.splitElementUntil(
            targetNode,
            targetOffset,
            blockToSplit.parentElement
        );
        restore();
        const removeEmptyAndFill = (node) => {
            if (!isBlock(node) && !isVisible(node)) {
                const parent = node.parentElement;
                node.remove();
                removeEmptyAndFill(parent);
            } else {
                fillEmpty(node);
            }
        };
        removeEmptyAndFill(lastLeaf(beforeElement));
        removeEmptyAndFill(firstLeaf(afterElement));

        this.shared.setCursorStart(afterElement);

        return [beforeElement, afterElement];
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
        this.dispatch("CLEAN", { root: element });
        // const before = /** @type {HTMLElement} **/ (element.cloneNode());
        /** @type {HTMLElement} **/
        const before = element.cloneNode();
        const after = /** @type {HTMLElement} **/ (element.cloneNode());
        let index = 0;
        for (const child of [...element.childNodes]) {
            index < offset ? before.appendChild(child) : after.appendChild(child);
            index++;
        }
        element.before(before);
        element.after(after);
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

    /**
     * Splits a text node in two parts.
     * If the split occurs at the beginning or the end, the text node stays
     * untouched and unsplit. If a split actually occurs, the original text node
     * still exists and become the right part of the split.
     *
     * Note: if split after or before whitespace, that whitespace may become
     * invisible, it is up to the caller to replace it by nbsp if needed.
     *
     * @param {Text} textNode
     * @param {number} offset
     * @param {boolean} originalNodeSide Whether the original node ends up on left
     * or right after the split
     * @returns {number} The parentOffset if the cursor was between the two text
     *          node parts after the split.
     */
    splitTextNode(textNode, offset, originalNodeSide = DIRECTIONS.RIGHT) {
        const document = textNode.ownerDocument;
        let parentOffset = childNodeIndex(textNode);

        if (offset > 0) {
            parentOffset++;

            if (offset < textNode.length) {
                const left = textNode.nodeValue.substring(0, offset);
                const right = textNode.nodeValue.substring(offset);
                if (originalNodeSide === DIRECTIONS.LEFT) {
                    const newTextNode = document.createTextNode(right);
                    textNode.after(newTextNode);
                    textNode.nodeValue = left;
                } else {
                    const newTextNode = document.createTextNode(left);
                    textNode.before(newTextNode);
                    textNode.nodeValue = right;
                }
            }
        }
        return parentOffset;
    }

    splitSelection() {
        let { startContainer, startOffset, endContainer, endOffset, direction } =
            this.shared.getEditableSelection();
        const isInSingleContainer = startContainer === endContainer;
        if (
            endContainer.nodeType === Node.TEXT_NODE &&
            endOffset !== 0 &&
            endOffset !== endContainer.textContent.length
        ) {
            const endParent = endContainer.parentNode;
            const splitOffset = this.splitTextNode(endContainer, endOffset);
            endContainer = endParent.childNodes[splitOffset - 1] || endParent.firstChild;
            if (isInSingleContainer) {
                startContainer = endContainer;
            }
            endOffset = endContainer.textContent.length;
        }
        if (
            startContainer.nodeType === Node.TEXT_NODE &&
            startOffset !== 0 &&
            startOffset !== startContainer.textContent.length
        ) {
            this.splitTextNode(startContainer, startOffset);
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
        return this.shared.setSelection(selection, { normalize: false });
    }

    onBeforeInput(e) {
        if (e.inputType === "insertParagraph") {
            e.preventDefault();
            this._splitBlock();
        }
    }
}
