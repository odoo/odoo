import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import {
    cleanTrailingBR,
    fillEmpty,
    fillShrunkPhrasingParent,
    makeContentsInline,
    removeClass,
    setTagName,
    unwrapContents,
} from "../utils/dom";
import {
    allowsParagraphRelatedElements,
    getDeepestPosition,
    isEmptyBlock,
    isSelfClosingElement,
    isShrunkBlock,
    paragraphRelatedElements,
} from "../utils/dom_info";
import { closestElement, descendants, firstLeaf, lastLeaf } from "../utils/dom_traversal";
import { FONT_SIZE_CLASSES, TEXT_STYLE_CLASSES } from "../utils/formatting";
import { DIRECTIONS, childNodeIndex, nodeSize, rightPos } from "../utils/position";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

export class DomPlugin extends Plugin {
    static name = "dom";
    static dependencies = ["selection", "split"];
    static shared = ["domInsert", "copyAttributes"];
    static resources = () => ({
        powerboxItems: {
            name: _t("Separator"),
            description: _t("Insert a horizontal rule separator"),
            category: "structure",
            fontawesome: "fa-minus",
            action(dispatch) {
                dispatch("INSERT_SEPARATOR");
            },
        },
    });
    contentEditableToRemove = new Set();

    handleCommand(command, payload) {
        switch (command) {
            case "SET_TAG":
                this.setTag(payload);
                break;
            case "INSERT_FONT_AWESOME":
                this.insertFontAwesome(payload.faClass);
                break;
            case "INSERT_SEPARATOR":
                this.insertSeparator();
                break;
            case "CLEAN":
                this.removeEmptyClassAndStyleAttributes(payload.root);
                break;
            case "CLEAN_FOR_SAVE": {
                this.removeEmptyClassAndStyleAttributes(payload.root);
                for (const el of payload.root.querySelectorAll("hr[contenteditable]")) {
                    el.removeAttribute("contenteditable");
                }
                break;
            }
            case "NORMALIZE": {
                // TODO @phoenix: payload.node is expected to be an Element, rename ?
                if (payload.node.tagName === "HR") {
                    const node = payload.node;
                    node.setAttribute(
                        "contenteditable",
                        node.hasAttribute("contenteditable")
                            ? node.getAttribute("contenteditable")
                            : "false"
                    );
                } else {
                    for (const separator of payload.node.querySelectorAll("hr")) {
                        separator.setAttribute(
                            "contenteditable",
                            separator.hasAttribute("contenteditable")
                                ? separator.getAttribute("contenteditable")
                                : "false"
                        );
                    }
                }
                break;
            }
        }
    }

    // Shared

    /**
     * @param {string | DocumentFragment | null} content
     */
    domInsert(content) {
        if (!content) {
            return;
        }
        let selection = this.shared.getEditableSelection();
        let startNode;
        let insertBefore = false;
        if (!selection.isCollapsed) {
            this.dispatch("DELETE_SELECTION", { selection });
            selection = this.shared.getEditableSelection();
        }
        if (selection.startContainer.nodeType === Node.TEXT_NODE) {
            insertBefore = !selection.startOffset;
            this.shared.splitTextNode(
                selection.startContainer,
                selection.startOffset,
                DIRECTIONS.LEFT
            );
            startNode = selection.startContainer;
        }

        const container = this.document.createElement("fake-element");
        const containerFirstChild = this.document.createElement("fake-element-fc");
        const containerLastChild = this.document.createElement("fake-element-lc");

        if (typeof content === "string") {
            container.textContent = content;
        } else {
            for (const child of content.children) {
                this.dispatch("NORMALIZE", { node: child });
            }
            container.replaceChildren(content);
        }

        // In case the html inserted starts with a list and will be inserted within
        // a list, unwrap the list elements from the list.
        if (
            closestElement(selection.anchorNode, "UL, OL") &&
            (container.firstChild.nodeName === "UL" || container.firstChild.nodeName === "OL")
        ) {
            container.replaceChildren(...container.firstChild.childNodes);
        }

        startNode = startNode || this.shared.getEditableSelection().anchorNode;
        const block = closestBlock(selection.anchorNode);

        const shouldUnwrap = (node) =>
            [...paragraphRelatedElements, "LI"].includes(node.nodeName) &&
            block.textContent !== "" &&
            node.textContent !== "" &&
            [node.nodeName, "DIV"].includes(block.nodeName) &&
            // If the selection anchorNode is the editable itself, the content
            // should not be unwrapped.
            selection.anchorNode !== this.editable;

        // Empty block must contain a br element to allow cursor placement.
        if (
            container.lastElementChild &&
            isBlock(container.lastElementChild) &&
            !container.lastElementChild.hasChildNodes()
        ) {
            fillEmpty(container.lastElementChild);
        }

        // In case the html inserted is all contained in a single root <p> or <li>
        // tag, we take the all content of the <p> or <li> and avoid inserting the
        // <p> or <li>.
        if (
            container.childElementCount === 1 &&
            (["P", "LI"].includes(container.firstChild.nodeName) ||
                shouldUnwrap(container.firstChild)) &&
            selection.anchorNode !== this.editable
        ) {
            const p = container.firstElementChild;
            container.replaceChildren(...p.childNodes);
        } else if (container.childElementCount > 1) {
            const isSelectionAtStart =
                firstLeaf(block) === selection.anchorNode && selection.anchorOffset === 0;
            const isSelectionAtEnd =
                lastLeaf(block) === selection.focusNode &&
                selection.focusOffset === nodeSize(selection.focusNode);
            // Grab the content of the first child block and isolate it.
            if (shouldUnwrap(container.firstChild) && !isSelectionAtStart) {
                containerFirstChild.replaceChildren(...container.firstElementChild.childNodes);
                container.firstElementChild.remove();
            }
            // Grab the content of the last child block and isolate it.
            if (shouldUnwrap(container.lastChild) && !isSelectionAtEnd) {
                containerLastChild.replaceChildren(...container.lastElementChild.childNodes);
                container.lastElementChild.remove();
            }
        }

        if (startNode.nodeType === Node.ELEMENT_NODE) {
            if (selection.anchorOffset === 0) {
                const textNode = this.document.createTextNode("");
                if (isSelfClosingElement(startNode)) {
                    startNode.parentNode.insertBefore(textNode, startNode);
                } else {
                    startNode.prepend(textNode);
                }
                startNode = textNode;
            } else {
                startNode = startNode.childNodes[selection.anchorOffset - 1];
            }
        }

        // If we have isolated block content, first we split the current focus
        // element if it's a block then we insert the content in the right places.
        let currentNode = startNode;
        let lastChildNode = false;
        const _insertAt = (reference, nodes, insertBefore) => {
            for (const child of insertBefore ? nodes.reverse() : nodes) {
                reference[insertBefore ? "before" : "after"](child);
                reference = child;
            }
        };
        const lastInsertedNodes = [...containerLastChild.childNodes];
        if (containerLastChild.hasChildNodes()) {
            const toInsert = [...containerLastChild.childNodes]; // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = insertBefore ? toInsert[0] : currentNode;
            lastChildNode = toInsert[toInsert.length - 1];
        }
        const firstInsertedNodes = [...containerFirstChild.childNodes];
        if (containerFirstChild.hasChildNodes()) {
            const toInsert = [...containerFirstChild.childNodes]; // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = toInsert[toInsert.length - 1];
            insertBefore = false;
        }

        // If all the Html have been isolated, We force a split of the parent element
        // to have the need new line in the final result
        if (!container.hasChildNodes()) {
            if (this.shared.isUnsplittable(closestBlock(currentNode.nextSibling))) {
                this.dispatch("INSERT_LINEBREAK_NODE", {
                    targetNode: currentNode.nextSibling,
                    targetOffset: 0,
                });
            } else {
                // If we arrive here, the o_enter index should always be 0.
                const parent = currentNode.nextSibling.parentElement;
                const index = [...parent.childNodes].indexOf(currentNode.nextSibling);
                this.dispatch("SPLIT_BLOCK_NODE", {
                    targetNode: currentNode.nextSibling.parentElement,
                    targetOffset: index,
                });
            }
        }

        let nodeToInsert;
        let doesCurrentNodeAllowsP = allowsParagraphRelatedElements(currentNode);
        const insertedNodes = [...container.childNodes];
        while ((nodeToInsert = container.firstChild)) {
            if (isBlock(nodeToInsert) && !doesCurrentNodeAllowsP) {
                // Split blocks at the edges if inserting new blocks (preventing
                // <p><p>text</p></p> or <li><li>text</li></li> scenarios).
                while (
                    !this.isEditionBoundary(currentNode.parentElement) &&
                    (!allowsParagraphRelatedElements(currentNode.parentElement) ||
                        currentNode.parentElement.nodeName === "LI")
                ) {
                    if (this.shared.isUnsplittable(currentNode.parentElement)) {
                        // If we have to insert a table, we cannot afford to unwrap it
                        // we need to search for a more suitable spot to put the table in
                        if (nodeToInsert.nodeName === "TABLE") {
                            currentNode = currentNode.parentElement;
                            doesCurrentNodeAllowsP = allowsParagraphRelatedElements(currentNode);
                            continue;
                        } else {
                            makeContentsInline(container);
                            nodeToInsert = container.childNodes[0];
                            break;
                        }
                    }
                    let offset = childNodeIndex(currentNode);
                    if (!insertBefore) {
                        offset += 1;
                    }
                    if (offset) {
                        const [left, right] = this.shared.splitElement(
                            currentNode.parentElement,
                            offset
                        );
                        currentNode = insertBefore ? right : left;
                        const otherNode = insertBefore ? left : right;
                        if (
                            this.shared.isUnsplittable(nodeToInsert) &&
                            container.childNodes.length === 1
                        ) {
                            fillShrunkPhrasingParent(otherNode);
                        } else if (isEmptyBlock(otherNode)) {
                            otherNode.remove();
                        }
                        if (otherNode.nodeType === Node.ELEMENT_NODE) {
                            cleanTrailingBR(otherNode);
                        }
                    } else {
                        if (isBlock(currentNode)) {
                            fillShrunkPhrasingParent(currentNode);
                        }
                        if (currentNode.nodeType === Node.ELEMENT_NODE) {
                            cleanTrailingBR(currentNode);
                        }
                        currentNode = currentNode.parentElement;
                    }
                    doesCurrentNodeAllowsP = allowsParagraphRelatedElements(currentNode);
                }
            }
            if (insertBefore) {
                currentNode.before(nodeToInsert);
                insertBefore = false;
            } else {
                currentNode.after(nodeToInsert);
            }
            if (
                nodeToInsert.nodeType !== Node.ELEMENT_NODE ||
                nodeToInsert.tagName !== "BR" ||
                nodeToInsert.nextSibling
            ) {
                // Avoid cleaning the trailing BR if it is nodeToInsert
                cleanTrailingBR(currentNode.parentElement);
            }
            if (currentNode.tagName !== "BR" && isShrunkBlock(currentNode)) {
                currentNode.remove();
            }
            currentNode = nodeToInsert;
        }
        const previousNode = currentNode.previousSibling;
        if (cleanTrailingBR(currentNode.parentElement)) {
            // Clean the last inserted trailing BR if any
            currentNode = previousNode;
        }
        currentNode = lastChildNode || currentNode;
        let lastPosition = [...paragraphRelatedElements, "LI"].includes(currentNode.nodeName)
            ? rightPos(lastLeaf(currentNode))
            : rightPos(currentNode);

        if (!this.config.allowInlineAtRoot && this.isEditionBoundary(lastPosition[0])) {
            // Correct the position if it happens to be in the editable root.
            lastPosition = getDeepestPosition(...lastPosition);
        }
        this.shared.setSelection(
            { anchorNode: lastPosition[0], anchorOffset: lastPosition[1] },
            { normalize: false }
        );
        return firstInsertedNodes.concat(insertedNodes).concat(lastInsertedNodes);
    }

    isEditionBoundary(node) {
        if (node === this.editable) {
            return true;
        }
        return node.hasAttribute("contenteditable");
    }

    copyAttributes(source, target) {
        this.dispatch("CLEAN", { root: source });
        for (const attr of source.attributes) {
            if (attr.name === "class") {
                target.classList.add(...source.classList);
            } else {
                target.setAttribute(attr.name, attr.value);
            }
        }
    }

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------

    insertFontAwesome(faClass = "fa fa-star") {
        const fontAwesomeNode = document.createElement("i");
        fontAwesomeNode.className = faClass;
        this.domInsert(fontAwesomeNode);
        this.dispatch("ADD_STEP");
        const [anchorNode, anchorOffset] = rightPos(fontAwesomeNode);
        this.shared.setSelection({ anchorNode, anchorOffset });
    }

    setTag({ tagName, extraClass = "" }) {
        tagName = tagName.toUpperCase();
        const cursors = this.shared.preserveSelection();
        const selectedBlocks = [...this.shared.getTraversedBlocks()];
        const deepestSelectedBlocks = selectedBlocks.filter(
            (block) =>
                !descendants(block).some((descendant) => selectedBlocks.includes(descendant)) &&
                block.isContentEditable
        );
        for (const block of deepestSelectedBlocks) {
            if (
                ["P", "PRE", "H1", "H2", "H3", "H4", "H5", "H6", "LI", "BLOCKQUOTE"].includes(
                    block.nodeName
                )
            ) {
                if (tagName === "P") {
                    if (block.nodeName === "LI") {
                        continue;
                    } else if (block.parentNode.nodeName === "LI") {
                        cursors.update(callbacksForCursorUpdate.unwrap(block));
                        unwrapContents(block);
                        continue;
                    }
                }

                const newEl = setTagName(block, tagName);
                cursors.remapNode(block, newEl);
                // We want to be able to edit the case `<h2 class="h3">`
                // but in that case, we want to display "Header 2" and
                // not "Header 3" as it is more important to display
                // the semantic tag being used (especially for h1 ones).
                // This is why those are not in `TEXT_STYLE_CLASSES`.
                const headingClasses = ["h1", "h2", "h3", "h4", "h5", "h6"];
                removeClass(newEl, ...FONT_SIZE_CLASSES, ...TEXT_STYLE_CLASSES, ...headingClasses);
                delete newEl.style.fontSize;
                if (extraClass) {
                    newEl.classList.add(extraClass);
                }
            } else {
                // eg do not change a <div> into a h1: insert the h1
                // into it instead.
                const newBlock = this.document.createElement(tagName);
                newBlock.append(...block.childNodes);
                block.append(newBlock);
                cursors.remapNode(block, newBlock);
            }
        }
        cursors.restore();
        this.dispatch("ADD_STEP");
    }

    insertSeparator() {
        const selection = this.shared.getEditableSelection();
        const sep = this.document.createElement("hr");
        const block = closestBlock(selection.startContainer);
        const element =
            closestElement(selection.startContainer, (el) =>
                paragraphRelatedElements.includes(el.tagName)
            ) || (block && block.nodeName !== "LI" ? block : null);

        if (element && element !== this.editable) {
            element.before(sep);
        }
        this.dispatch("ADD_STEP");
    }

    removeEmptyClassAndStyleAttributes(root) {
        for (const node of [root, ...descendants(root)]) {
            if (node.classList && !node.classList.length) {
                node.removeAttribute("class");
            }
            if (node.style && !node.style.length) {
                node.removeAttribute("style");
            }
        }
    }
}
