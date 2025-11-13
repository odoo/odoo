import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import {
    cleanTrailingBR,
    fillEmpty,
    fillShrunkPhrasingParent,
    makeContentsInline,
    removeClass,
    removeStyle,
    splitTextNode,
    unwrapContents,
    wrapInlinesInBlocks,
} from "../utils/dom";
import {
    allowsParagraphRelatedElements,
    getDeepestPosition,
    isContentEditable,
    isContentEditableAncestor,
    isEmptyBlock,
    isListElement,
    isListItemElement,
    isParagraphRelatedElement,
    isProtecting,
    isProtected,
    isSelfClosingElement,
    isShrunkBlock,
    isTangible,
    isUnprotecting,
    listElementSelector,
    isEditorTab,
    isPhrasingContent,
} from "../utils/dom_info";
import {
    childNodes,
    children,
    closestElement,
    descendants,
    firstLeaf,
    lastLeaf,
} from "../utils/dom_traversal";
import { FONT_SIZE_CLASSES, TEXT_STYLE_CLASSES } from "../utils/formatting";
import { DIRECTIONS, childNodeIndex, nodeSize, rightPos } from "../utils/position";
import { normalizeCursorPosition } from "@html_editor/utils/selection";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

/**
 * Get distinct connected parents of nodes
 *
 * @param {Iterable} nodes
 * @returns {Set}
 */
function getConnectedParents(nodes) {
    const parents = new Set();
    for (const node of nodes) {
        if (node.isConnected && node.parentElement) {
            parents.add(node.parentElement);
        }
    }
    return parents;
}

/**
 * @typedef {Object} DomShared
 * @property { DomPlugin['insert'] } insert
 * @property { DomPlugin['copyAttributes'] } copyAttributes
 * @property { DomPlugin['canSetBlock'] } canSetBlock
 * @property { DomPlugin['setBlock'] } setBlock
 * @property { DomPlugin['setTagName'] } setTagName
 * @property { DomPlugin['removeSystemProperties'] } removeSystemProperties
 */

export class DomPlugin extends Plugin {
    static id = "dom";
    static dependencies = ["baseContainer", "selection", "history", "split", "delete", "lineBreak"];
    static shared = [
        "insert",
        "copyAttributes",
        "canSetBlock",
        "setBlock",
        "setTagName",
        "removeSystemProperties",
    ];
    resources = {
        user_commands: [
            {
                id: "insertFontAwesome",
                run: this.insertFontAwesome.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "setTag",
                run: this.setBlock.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        /** Handlers */
        clean_for_save_handlers: ({ root }) => {
            this.removeEmptyClassAndStyleAttributes(root);
        },
        clipboard_content_processors: this.removeEmptyClassAndStyleAttributes.bind(this),
        functional_empty_node_predicates: [isSelfClosingElement, isEditorTab],
    };

    setup() {
        this.systemClasses = this.getResource("system_classes");
        this.systemAttributes = this.getResource("system_attributes");
        this.systemStyleProperties = this.getResource("system_style_properties");
        this.systemPropertiesSelector = [
            ...this.systemClasses.map((className) => `.${className}`),
            ...this.systemAttributes.map((attr) => `[${attr}]`),
            ...this.systemStyleProperties.map((prop) => `[style*="${prop}"]`),
        ].join(",");
    }

    // Shared

    /**
     * @param {string | DocumentFragment | Element | null} content
     */
    insert(content) {
        if (!content) {
            return;
        }
        let selection = this.dependencies.selection.getEditableSelection();
        if (!selection.isCollapsed) {
            this.dependencies.delete.deleteSelection();
            selection = this.dependencies.selection.getEditableSelection();
        }

        let container = this.document.createElement("fake-element");
        const containerFirstChild = this.document.createElement("fake-element-fc");
        const containerLastChild = this.document.createElement("fake-element-lc");
        if (typeof content === "string") {
            container.textContent = content;
        } else {
            if (content.nodeType === Node.ELEMENT_NODE) {
                this.dispatchTo("normalize_handlers", content);
            } else {
                for (const child of children(content)) {
                    this.dispatchTo("normalize_handlers", child);
                }
            }
            container.replaceChildren(content);
        }

        const block = closestBlock(selection.anchorNode);
        for (const cb of this.getResource("before_insert_processors")) {
            container = cb(container, block);
        }
        selection = this.dependencies.selection.getEditableSelection();

        let startNode;
        let insertBefore = false;
        if (selection.startContainer.nodeType === Node.TEXT_NODE) {
            insertBefore = !selection.startOffset;
            splitTextNode(selection.startContainer, selection.startOffset, DIRECTIONS.LEFT);
            startNode = selection.startContainer;
        }

        const allInsertedNodes = [];
        // In case the html inserted starts with a list and will be inserted within
        // a list, unwrap the list elements from the list.
        const hasSingleChild = nodeSize(container) === 1;
        if (
            closestElement(selection.anchorNode, listElementSelector) &&
            isListElement(container.firstChild)
        ) {
            unwrapContents(container.firstChild);
        }
        // Similarly if the html inserted ends with a list.
        if (
            closestElement(selection.focusNode, listElementSelector) &&
            isListElement(container.lastChild) &&
            !hasSingleChild
        ) {
            unwrapContents(container.lastChild);
        }

        startNode = startNode || this.dependencies.selection.getEditableSelection().anchorNode;

        const shouldUnwrap = (node) =>
            (isParagraphRelatedElement(node) || isListItemElement(node)) &&
            !isEmptyBlock(block) &&
            !isEmptyBlock(node) &&
            (isContentEditable(node) ||
                (!node.isConnected && !closestElement(node, "[contenteditable]"))) &&
            !this.dependencies.split.isUnsplittable(node) &&
            (node.nodeName === block.nodeName ||
                (this.dependencies.baseContainer.isCandidateForBaseContainer(node) &&
                    this.dependencies.baseContainer.isCandidateForBaseContainer(block)) ||
                block.nodeName === "PRE" ||
                (block.nodeName === "DIV" && this.dependencies.split.isUnsplittable(block))) &&
            // If the selection anchorNode is the editable itself, the content
            // should not be unwrapped.
            !this.isEditionBoundary(selection.anchorNode);

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
            (this.dependencies.baseContainer.isCandidateForBaseContainer(container.firstChild) ||
                shouldUnwrap(container.firstChild))
        ) {
            const nodeToUnwrap = container.firstElementChild;
            container.replaceChildren(...childNodes(nodeToUnwrap));
        } else if (container.childElementCount > 1) {
            const isSelectionAtStart =
                firstLeaf(block) === selection.anchorNode && selection.anchorOffset === 0;
            const isSelectionAtEnd =
                lastLeaf(block) === selection.focusNode &&
                selection.focusOffset === nodeSize(selection.focusNode);
            // Grab the content of the first child block and isolate it.
            if (shouldUnwrap(container.firstChild) && !isSelectionAtStart) {
                // Unwrap the deepest nested first <li> element in the
                // container to extract and paste the text content of the list.
                if (isListItemElement(container.firstChild)) {
                    const deepestBlock = closestBlock(firstLeaf(container.firstChild));
                    this.dependencies.split.splitAroundUntil(deepestBlock, container.firstChild);
                    container.firstElementChild.replaceChildren(...childNodes(deepestBlock));
                }
                containerFirstChild.replaceChildren(...childNodes(container.firstElementChild));
                container.firstElementChild.remove();
            }
            // Grab the content of the last child block and isolate it.
            if (shouldUnwrap(container.lastChild) && !isSelectionAtEnd) {
                // Unwrap the deepest nested last <li> element in the container
                // to extract and paste the text content of the list.
                if (isListItemElement(container.lastChild)) {
                    const deepestBlock = closestBlock(lastLeaf(container.lastChild));
                    this.dependencies.split.splitAroundUntil(deepestBlock, container.lastChild);
                    container.lastElementChild.replaceChildren(...childNodes(deepestBlock));
                }
                containerLastChild.replaceChildren(...childNodes(container.lastElementChild));
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
                allInsertedNodes.push(textNode);
            } else {
                startNode = childNodes(startNode).at(selection.anchorOffset - 1);
            }
        }

        // If we have isolated block content, first we split the current focus
        // element if it's a block then we insert the content in the right places.
        let currentNode = startNode;
        const _insertAt = (reference, nodes, insertBefore) => {
            for (const child of insertBefore ? nodes.reverse() : nodes) {
                reference[insertBefore ? "before" : "after"](child);
                reference = child;
            }
        };
        const lastInsertedNodes = childNodes(containerLastChild);
        if (containerLastChild.hasChildNodes()) {
            const toInsert = childNodes(containerLastChild); // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = insertBefore ? toInsert[0] : currentNode;
            toInsert[toInsert.length - 1];
        }
        const firstInsertedNodes = childNodes(containerFirstChild);
        if (containerFirstChild.hasChildNodes()) {
            const toInsert = childNodes(containerFirstChild); // Prevent mutation
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = toInsert[toInsert.length - 1];
            insertBefore = false;
        }
        allInsertedNodes.push(...firstInsertedNodes);

        // If all the Html have been isolated, We force a split of the parent element
        // to have the need new line in the final result
        if (!container.hasChildNodes()) {
            if (this.dependencies.split.isUnsplittable(closestBlock(currentNode.nextSibling))) {
                this.dependencies.lineBreak.insertLineBreakNode({
                    targetNode: currentNode.nextSibling,
                    targetOffset: 0,
                });
            } else {
                // If we arrive here, the o_enter index should always be 0.
                const parent = currentNode.nextSibling.parentElement;
                const index = childNodes(parent).indexOf(currentNode.nextSibling);
                this.dependencies.split.splitBlockNode({
                    targetNode: parent,
                    targetOffset: index,
                });
            }
        }

        let nodeToInsert;
        let doesCurrentNodeAllowsP = allowsParagraphRelatedElements(currentNode);
        const candidatesForRemoval = [];
        const insertedNodes = childNodes(container);
        while ((nodeToInsert = container.firstChild)) {
            if (isBlock(nodeToInsert) && !doesCurrentNodeAllowsP) {
                // Split blocks at the edges if inserting new blocks (preventing
                // <p><p>text</p></p> or <li><li>text</li></li> scenarios).
                while (
                    !this.isEditionBoundary(currentNode.parentElement) &&
                    (!allowsParagraphRelatedElements(currentNode.parentElement) ||
                        (isListItemElement(currentNode.parentElement) &&
                            !this.dependencies.split.isUnsplittable(nodeToInsert)))
                ) {
                    if (this.dependencies.split.isUnsplittable(currentNode.parentElement)) {
                        // If we have to insert an unsplittable element, we cannot afford to
                        // unwrap it we need to search for a more suitable spot to put it
                        if (this.dependencies.split.isUnsplittable(nodeToInsert)) {
                            currentNode = currentNode.parentElement;
                            doesCurrentNodeAllowsP = allowsParagraphRelatedElements(currentNode);
                            continue;
                        } else {
                            makeContentsInline(container);
                            nodeToInsert = container.firstChild;
                            break;
                        }
                    }
                    let offset = childNodeIndex(currentNode);
                    if (!insertBefore) {
                        offset += 1;
                    }
                    if (offset) {
                        const [left, right] = this.dependencies.split.splitElement(
                            currentNode.parentElement,
                            offset
                        );
                        currentNode = insertBefore ? right : left;
                        const otherNode = insertBefore ? left : right;
                        if (isBlock(otherNode)) {
                            fillShrunkPhrasingParent(otherNode);
                        }
                        // After the content insertion, the right-part of a
                        // split is evaluated for removal.
                        candidatesForRemoval.push(right);
                    } else {
                        if (isBlock(currentNode)) {
                            fillShrunkPhrasingParent(currentNode);
                        }
                        currentNode = currentNode.parentElement;
                    }
                    doesCurrentNodeAllowsP = allowsParagraphRelatedElements(currentNode);
                }
                if (
                    isListItemElement(currentNode.parentElement) &&
                    isBlock(nodeToInsert) &&
                    this.dependencies.split.isUnsplittable(nodeToInsert)
                ) {
                    const br = document.createElement("br");
                    currentNode[
                        isEmptyBlock(currentNode) || !isTangible(currentNode) ? "before" : "after"
                    ](br);
                }
            }
            // Ensure that all adjacent paragraph elements are converted to
            // <li> when inserting in a list.
            const block = closestBlock(currentNode);
            for (const processor of this.getResource("node_to_insert_processors")) {
                nodeToInsert = processor({ nodeToInsert, container: block });
            }
            if (insertBefore) {
                currentNode.before(nodeToInsert);
                insertBefore = false;
            } else {
                currentNode.after(nodeToInsert);
            }
            allInsertedNodes.push(nodeToInsert);
            if (currentNode.tagName !== "BR" && isShrunkBlock(currentNode)) {
                currentNode.remove();
            }
            currentNode = nodeToInsert;
        }
        allInsertedNodes.push(...lastInsertedNodes);
        this.getResource("after_insert_handlers").forEach((handler) => handler(allInsertedNodes));
        let insertedNodesParents = getConnectedParents(allInsertedNodes);
        for (const parent of insertedNodesParents) {
            if (
                !this.config.allowInlineAtRoot &&
                this.isEditionBoundary(parent) &&
                allowsParagraphRelatedElements(parent)
            ) {
                // Ensure that edition boundaries do not have inline content.
                wrapInlinesInBlocks(parent, {
                    baseContainerNodeName: this.dependencies.baseContainer.getDefaultNodeName(),
                });
            }
        }
        insertedNodesParents = getConnectedParents(allInsertedNodes);
        for (const parent of insertedNodesParents) {
            if (
                !isProtecting(parent) &&
                !(isProtected(parent) && !isUnprotecting(parent)) &&
                parent.isContentEditable
            ) {
                cleanTrailingBR(parent);
            }
        }
        for (const candidateForRemoval of candidatesForRemoval) {
            if (
                candidateForRemoval.isConnected &&
                (isParagraphRelatedElement(candidateForRemoval) ||
                    isListItemElement(candidateForRemoval)) &&
                candidateForRemoval.parentElement.isContentEditable &&
                isEmptyBlock(candidateForRemoval)
            ) {
                candidateForRemoval.remove();
            }
        }
        for (const insertedNode of allInsertedNodes.reverse()) {
            if (insertedNode.isConnected) {
                currentNode = insertedNode;
                break;
            }
        }
        let lastPosition =
            isParagraphRelatedElement(currentNode) ||
            isListItemElement(currentNode) ||
            isListElement(currentNode)
                ? rightPos(lastLeaf(currentNode))
                : rightPos(currentNode);
        lastPosition = normalizeCursorPosition(lastPosition[0], lastPosition[1], "right");

        if (!this.config.allowInlineAtRoot && this.isEditionBoundary(lastPosition[0])) {
            // Correct the position if it happens to be in the editable root.
            lastPosition = getDeepestPosition(...lastPosition);
        }
        this.dependencies.selection.setSelection(
            { anchorNode: lastPosition[0], anchorOffset: lastPosition[1] },
            { normalize: false }
        );
        return firstInsertedNodes.concat(insertedNodes).concat(lastInsertedNodes);
    }

    isEditionBoundary(node) {
        if (!node) {
            return false;
        }
        if (node === this.editable) {
            return true;
        }
        return isContentEditableAncestor(node);
    }

    /**
     * @param {HTMLElement} source
     * @param {HTMLElement} target
     */
    copyAttributes(source, target) {
        if (source?.nodeType !== Node.ELEMENT_NODE || target?.nodeType !== Node.ELEMENT_NODE) {
            return;
        }
        const ignoredAttrs = new Set(this.getResource("system_attributes"));
        const ignoredClasses = new Set(this.getResource("system_classes"));
        for (const attr of source.attributes) {
            if (ignoredAttrs.has(attr.name)) {
                continue;
            }
            if (attr.name !== "class" || ignoredClasses.size === 0) {
                target.setAttribute(attr.name, attr.value);
            } else {
                const classes = [...source.classList];
                for (const className of classes) {
                    if (!ignoredClasses.has(className)) {
                        target.classList.add(className);
                    }
                }
            }
        }
    }

    /**
     * Basic method to change an element tagName.
     * It is a technical function which only modifies a tag and its attributes.
     * It does not modify descendants nor handle the cursor.
     * @see setBlock for the more thorough command.
     *
     * @param {HTMLElement} el
     * @param {string} newTagName
     */
    setTagName(el, newTagName) {
        const document = el.ownerDocument;
        if (el.tagName === newTagName) {
            return el;
        }
        const newEl = document.createElement(newTagName);
        const content = childNodes(el);
        if (isListItemElement(el)) {
            el.append(newEl);
            newEl.replaceChildren(...content);
        } else {
            if (el.parentElement) {
                el.before(newEl);
            }
            this.copyAttributes(el, newEl);
            newEl.replaceChildren(...content);
            el.remove();
        }
        return newEl;
    }

    /**
     * Remove system-specific classes, attributes, and style properties from a
     * fragment or an element.
     *
     * @param {DocumentFragment|HTMLElement} root
     */
    removeSystemProperties(root) {
        const clean = (element) => {
            removeClass(element, ...this.systemClasses);
            this.systemAttributes.forEach((attr) => element.removeAttribute(attr));
            removeStyle(element, ...this.systemStyleProperties);
        };
        if (root.matches?.(this.systemPropertiesSelector)) {
            clean(root);
        }
        for (const element of root.querySelectorAll(this.systemPropertiesSelector)) {
            clean(element);
        }
    }

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------

    insertFontAwesome({ faClass = "fa fa-star" } = {}) {
        const fontAwesomeNode = document.createElement("i");
        fontAwesomeNode.className = faClass;
        this.insert(fontAwesomeNode);
        this.dependencies.history.addStep();
        const [anchorNode, anchorOffset] = rightPos(fontAwesomeNode);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
    }

    /**
     * Determines if a block element can be safely retagged.
     *
     * Certain blocks (like 'o_editable') should not be retagged because doing so
     * will recreate the block, potentially causing issues. This function checks
     * if retagging a block is safe.
     *
     * @param {HTMLElement} block
     * @returns {boolean}
     */
    isRetaggingSafe(block) {
        return !(
            (isParagraphRelatedElement(block) ||
                isListItemElement(block) ||
                isPhrasingContent(block)) &&
            this.getResource("unremovable_node_predicates").some((predicate) => predicate(block))
        );
    }

    getBlocksToSet() {
        const targetedBlocks = [...this.dependencies.selection.getTargetedBlocks()];
        return targetedBlocks.filter(
            (block) =>
                this.isRetaggingSafe(block) &&
                !descendants(block).some((descendant) => targetedBlocks.includes(descendant)) &&
                block.isContentEditable
        );
    }

    canSetBlock() {
        return this.getBlocksToSet().length > 0;
    }

    /**
     * @param {Object} param0
     * @param {string} param0.tagName
     * @param {string} [param0.extraClass]
     */
    setBlock({ tagName, extraClass = "" }) {
        let newCandidate = this.document.createElement(tagName.toUpperCase());
        if (extraClass) {
            newCandidate.classList.add(extraClass);
        }
        if (this.dependencies.baseContainer.isCandidateForBaseContainer(newCandidate)) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer(
                newCandidate.nodeName
            );
            this.copyAttributes(newCandidate, baseContainer);
            newCandidate = baseContainer;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        const newEls = [];
        for (const block of this.getBlocksToSet()) {
            if (
                isParagraphRelatedElement(block) ||
                isListItemElement(block) ||
                isPhrasingContent(block) ||
                block.nodeName === "BLOCKQUOTE"
            ) {
                if (newCandidate.matches(baseContainerGlobalSelector) && isListItemElement(block)) {
                    continue;
                }
                this.dispatchTo("before_set_tag_handlers", block);
                const newEl = this.setTagName(block, tagName);
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
                newEls.push(newEl);
            } else {
                // eg do not change a <div> into a h1: insert the h1
                // into it instead.
                newCandidate.append(...childNodes(block));
                block.append(newCandidate);
                cursors.remapNode(block, newCandidate);
            }
        }
        cursors.restore();
        this.dependencies.history.addStep();
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
