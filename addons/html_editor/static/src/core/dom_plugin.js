/** @odoo-module native */
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { normalizeCursorPosition } from "@html_editor/utils/selection";

import { Plugin } from "../plugin.js";
import { closestBlock, isBlock } from "../utils/blocks.js";
import {
    cleanTrailingBR,
    fillEmpty,
    fillShrunkPhrasingParent,
    makeContentsInline,
    removeClass,
    removeStyle,
    unwrapContents,
    wrapInlinesInBlocks,
} from "../utils/dom.js";
import {
    allowsParagraphRelatedElements,
    getDeepestEditablePosition,
    isContentEditable,
    isContentEditableAncestor,
    isEditorTab,
    isEmptyBlock,
    isListElement,
    isListItemElement,
    isParagraphRelatedElement,
    isPhrasingContent,
    isProtected,
    isProtecting,
    isSelfClosingElement,
    isShrunkBlock,
    isTangible,
    isUnprotecting,
} from "../utils/dom_info.js";
import {
    childNodes,
    children,
    closestElement,
    descendants,
    firstLeaf,
    lastLeaf,
} from "../utils/dom_traversal.js";
import { FONT_SIZE_CLASSES, TEXT_STYLE_CLASSES } from "../utils/formatting.js";
import { childNodeIndex, nodeSize, rightPos } from "../utils/position.js";

/**
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

/**
 * @typedef {((insertedNodes: Node[]) => void)[]} after_insert_handlers
 * @typedef {((el: HTMLElement) => void)[]} before_set_tag_handlers
 * @typedef {((container: Element, block: Element) => container)[]} before_insert_processors
 * @typedef {((arg: { nodeToInsert: Node, container: HTMLElement }) => nodeToInsert)[]} node_to_insert_processors
 * @typedef {((el: HTMLElement) => Promise<boolean>)[]} are_inlines_allowed_at_root_predicates
 * @typedef {string[]} system_attributes
 * @typedef {string[]} system_classes
 * @typedef {string[]} system_style_properties
 */

export class DomPlugin extends Plugin {
    static id = "dom";
    static dependencies = [
        "baseContainer",
        "selection",
        "history",
        "split",
        "delete",
        "lineBreak",
    ];
    static shared = [
        "insert",
        "copyAttributes",
        "canSetBlock",
        "setBlock",
        "setTagName",
        "removeSystemProperties",
    ];
    /** @type {import("plugins").EditorResources} */
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
        clean_for_save_handlers: ({ root }) => {
            this.removeEmptyClassAndStyleAttributes(root);
        },
        clipboard_content_processors:
            this.removeEmptyClassAndStyleAttributes.bind(this),
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

    /**
     * @param {string | DocumentFragment | Element | Text | null} content
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
        if (!container.hasChildNodes()) {
            return [];
        }
        selection = this.dependencies.selection.getEditableSelection();

        let startNode;
        let insertBefore = false;
        if (selection.startContainer.nodeType === Node.TEXT_NODE) {
            insertBefore = !selection.startOffset;
            if (
                selection.startOffset !== 0 &&
                selection.startOffset !== selection.startContainer.length
            ) {
                selection.startContainer.splitText(selection.startOffset);
            }
            startNode = selection.startContainer;
        }

        const allInsertedNodes = [];
        const hasSingleChild = nodeSize(container) === 1;
        const closestList = (node) => {
            if (isBlock(node)) {
                return node && isListItemElement(node);
            }
            return closestList(node.parentElement);
        };

        if (closestList(selection.anchorNode) && isListElement(container.firstChild)) {
            unwrapContents(container.firstChild);
        }
        if (
            closestList(selection.focusNode) &&
            isListElement(container.lastChild) &&
            !hasSingleChild
        ) {
            unwrapContents(container.lastChild);
        }

        startNode =
            startNode || this.dependencies.selection.getEditableSelection().anchorNode;

        const shouldUnwrap = (node) =>
            (isParagraphRelatedElement(node) || isListItemElement(node)) &&
            !isEmptyBlock(block) &&
            !isEmptyBlock(node) &&
            isContentEditable(block) &&
            (isContentEditable(node) ||
                (!node.isConnected && !closestElement(node, "[contenteditable]"))) &&
            !this.dependencies.split.isUnsplittable(node) &&
            (node.nodeName === block.nodeName ||
                (this.dependencies.baseContainer.isCandidateForBaseContainer(node) &&
                    this.dependencies.baseContainer.isCandidateForBaseContainer(
                        block,
                    )) ||
                block.nodeName === "PRE" ||
                (block.nodeName === "DIV" &&
                    this.dependencies.split.isUnsplittable(block))) &&
            !this.isEditionBoundary(selection.anchorNode);

        const firstLeafNode = firstLeaf(container);
        if (
            isBlock(firstLeafNode) &&
            !(
                closestElement(firstLeafNode, "[contenteditable]")?.contentEditable ===
                "false"
            )
        ) {
            fillEmpty(firstLeafNode);
        }
        const lastLeafNode = lastLeaf(container);
        if (
            isBlock(lastLeafNode) &&
            !(
                closestElement(lastLeafNode, "[contenteditable]")?.contentEditable ===
                "false"
            )
        ) {
            fillEmpty(lastLeafNode);
        }

        if (
            container.childElementCount === 1 &&
            (this.dependencies.baseContainer.isCandidateForBaseContainer(
                container.firstChild,
            ) ||
                shouldUnwrap(container.firstChild))
        ) {
            const nodeToUnwrap = container.firstElementChild;
            container.replaceChildren(...childNodes(nodeToUnwrap));
        } else if (container.childElementCount > 1) {
            const isSelectionAtStart =
                firstLeaf(block) === selection.anchorNode &&
                selection.anchorOffset === 0;
            const isSelectionAtEnd =
                lastLeaf(block) === selection.focusNode &&
                selection.focusOffset === nodeSize(selection.focusNode);
            if (shouldUnwrap(container.firstChild) && !isSelectionAtStart) {
                if (isListItemElement(container.firstChild)) {
                    const deepestBlock = closestBlock(firstLeaf(container.firstChild));
                    this.dependencies.split.splitAroundUntil(
                        deepestBlock,
                        container.firstChild,
                    );
                    container.firstElementChild.replaceChildren(
                        ...childNodes(deepestBlock),
                    );
                }
                containerFirstChild.replaceChildren(
                    ...childNodes(container.firstElementChild),
                );
                container.firstElementChild.remove();
            }
            if (shouldUnwrap(container.lastChild) && !isSelectionAtEnd) {
                if (isListItemElement(container.lastChild)) {
                    const deepestBlock = closestBlock(lastLeaf(container.lastChild));
                    this.dependencies.split.splitAroundUntil(
                        deepestBlock,
                        container.lastChild,
                    );
                    container.lastElementChild.replaceChildren(
                        ...childNodes(deepestBlock),
                    );
                }
                containerLastChild.replaceChildren(
                    ...childNodes(container.lastElementChild),
                );
                container.lastElementChild.remove();
            }
        }

        const textNode = this.document.createTextNode("");
        if (startNode.nodeType === Node.ELEMENT_NODE) {
            if (selection.anchorOffset === 0) {
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

        let currentNode = startNode;
        const _insertAt = (reference, nodes, insertBefore) => {
            for (const child of insertBefore ? nodes.reverse() : nodes) {
                reference[insertBefore ? "before" : "after"](child);
                reference = child;
            }
        };
        const lastInsertedNodes = childNodes(containerLastChild);
        if (containerLastChild.hasChildNodes()) {
            const toInsert = childNodes(containerLastChild);
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = insertBefore ? toInsert[0] : currentNode;
        }
        const firstInsertedNodes = childNodes(containerFirstChild);
        if (containerFirstChild.hasChildNodes()) {
            const toInsert = childNodes(containerFirstChild);
            _insertAt(currentNode, [...toInsert], insertBefore);
            currentNode = toInsert[toInsert.length - 1];
            insertBefore = false;
        }
        allInsertedNodes.push(...firstInsertedNodes);

        if (!container.hasChildNodes()) {
            if (
                this.dependencies.split.isUnsplittable(
                    closestBlock(currentNode.nextSibling),
                )
            ) {
                this.dependencies.lineBreak.insertLineBreakNode({
                    targetNode: currentNode.nextSibling,
                    targetOffset: 0,
                });
            } else {
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
                while (
                    !this.isEditionBoundary(currentNode) &&
                    (!allowsParagraphRelatedElements(currentNode.parentElement) ||
                        (isListItemElement(currentNode.parentElement) &&
                            !this.dependencies.split.isUnsplittable(nodeToInsert)))
                ) {
                    if (
                        this.dependencies.split.isUnsplittable(
                            currentNode.parentElement,
                        )
                    ) {
                        if (this.dependencies.split.isUnsplittable(nodeToInsert)) {
                            if (this.isEditionBoundary(currentNode.parentElement)) {
                                break;
                            }
                            currentNode = currentNode.parentElement;
                            doesCurrentNodeAllowsP =
                                allowsParagraphRelatedElements(currentNode);
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
                            offset,
                        );
                        currentNode = insertBefore ? right : left;
                        const otherNode = insertBefore ? left : right;
                        if (isBlock(otherNode)) {
                            fillShrunkPhrasingParent(otherNode);
                        }
                        candidatesForRemoval.push(right);
                    } else {
                        if (isBlock(currentNode)) {
                            fillShrunkPhrasingParent(currentNode);
                        }
                        currentNode = currentNode.parentElement;
                    }
                    doesCurrentNodeAllowsP =
                        allowsParagraphRelatedElements(currentNode);
                }
                if (
                    isListItemElement(currentNode.parentElement) &&
                    isBlock(nodeToInsert) &&
                    this.dependencies.split.isUnsplittable(nodeToInsert)
                ) {
                    const br = this.document.createElement("br");
                    currentNode[
                        isEmptyBlock(currentNode) || !isTangible(currentNode)
                            ? "before"
                            : "after"
                    ](br);
                }
            }
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
        textNode.remove();
        allInsertedNodes.push(...lastInsertedNodes);
        this.getResource("after_insert_handlers").forEach((handler) =>
            handler(allInsertedNodes),
        );
        let insertedNodesParents = getConnectedParents(allInsertedNodes);
        for (const parent of insertedNodesParents) {
            if (
                !this.areInlinesAllowedAtRoot(parent) &&
                this.isEditionBoundary(parent) &&
                allowsParagraphRelatedElements(parent)
            ) {
                wrapInlinesInBlocks(parent, {
                    baseContainerNodeName:
                        this.dependencies.baseContainer.getDefaultNodeName(),
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
        const lastInsertedNode = allInsertedNodes.findLast((node) => node.isConnected);
        if (!lastInsertedNode) {
            return;
        }
        let lastPosition =
            isParagraphRelatedElement(lastInsertedNode) ||
            isListItemElement(lastInsertedNode) ||
            isListElement(lastInsertedNode)
                ? rightPos(lastLeaf(lastInsertedNode))
                : rightPos(lastInsertedNode);
        lastPosition = normalizeCursorPosition(
            lastPosition[0],
            lastPosition[1],
            "right",
        );

        if (!this.config.allowInlineAtRoot && this.isEditionBoundary(lastPosition[0])) {
            lastPosition = getDeepestEditablePosition(...lastPosition);
        }
        this.dependencies.selection.setSelection(
            { anchorNode: lastPosition[0], anchorOffset: lastPosition[1] },
            { normalize: false },
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

    areInlinesAllowedAtRoot(node) {
        const results = this.getResource("are_inlines_allowed_at_root_predicates")
            .map((p) => p(node))
            .filter((r) => r !== undefined);
        if (!results.length) {
            return this.config.allowInlineAtRoot;
        }
        return results.every((r) => r);
    }

    /**
     * @param {HTMLElement} source
     * @param {HTMLElement} target
     */
    copyAttributes(source, target) {
        if (
            source?.nodeType !== Node.ELEMENT_NODE ||
            target?.nodeType !== Node.ELEMENT_NODE
        ) {
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

    insertFontAwesome({ faClass = "fa-solid fa-star" } = {}) {
        const fontAwesomeNode = this.document.createElement("i");
        fontAwesomeNode.className = faClass;
        this.insert(fontAwesomeNode);
        this.dependencies.history.addStep();
        const [anchorNode, anchorOffset] = rightPos(fontAwesomeNode);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
    }

    /**
     * @param {HTMLElement} block
     * @returns {boolean}
     */
    isRetaggingSafe(block) {
        return !(
            (isParagraphRelatedElement(block) ||
                isListItemElement(block) ||
                isPhrasingContent(block)) &&
            this.getResource("unremovable_node_predicates").some((predicate) =>
                predicate(block),
            )
        );
    }

    getBlocksToSet() {
        const isCollapsed =
            this.dependencies.selection.getEditableSelection().isCollapsed;
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const lastTargetedNode = targetedNodes.slice(-1)[0];
        const targetedBlocks = [
            ...new Set(targetedNodes.map(closestBlock).filter(Boolean)),
        ];
        return targetedBlocks.filter(
            (block) =>
                // If the selection ends in a block, the block is not visibly
                // selected so exclude it.
                (isCollapsed || block !== lastTargetedNode) &&
                this.isRetaggingSafe(block) &&
                !descendants(block).some((descendant) =>
                    targetedBlocks.includes(descendant),
                ) &&
                block.isContentEditable,
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
        const createNewCandidate = () => {
            let newCandidate = this.document.createElement(tagName.toUpperCase());
            if (extraClass) {
                newCandidate.classList.add(extraClass);
            }
            if (
                this.dependencies.baseContainer.isCandidateForBaseContainer(
                    newCandidate,
                )
            ) {
                const baseContainer =
                    this.dependencies.baseContainer.createBaseContainer(
                        newCandidate.nodeName,
                    );
                this.copyAttributes(newCandidate, baseContainer);
                newCandidate = baseContainer;
            }
            return newCandidate;
        };
        let newCandidate = createNewCandidate();
        this.dependencies.split.splitBlockSegments();
        const cursors = this.dependencies.selection.preserveSelection();
        const newEls = [];
        for (const block of this.getBlocksToSet()) {
            if (
                isParagraphRelatedElement(block) ||
                isListItemElement(block) ||
                isPhrasingContent(block) ||
                block.nodeName === "BLOCKQUOTE"
            ) {
                if (
                    newCandidate.matches(baseContainerGlobalSelector) &&
                    isListItemElement(block)
                ) {
                    continue;
                }
                this.dispatchTo("before_set_tag_handlers", block, tagName, cursors);
                const newEl = this.setTagName(block, tagName);
                cursors.remapNode(block, newEl);
                const headingClasses = ["h1", "h2", "h3", "h4", "h5", "h6"];
                removeClass(
                    newEl,
                    ...FONT_SIZE_CLASSES,
                    ...TEXT_STYLE_CLASSES,
                    ...headingClasses,
                );
                delete newEl.style.fontSize;
                if (extraClass) {
                    newEl.classList.add(extraClass);
                }
                newEls.push(newEl);
            } else {
                newCandidate.append(...childNodes(block));
                block.append(newCandidate);
                cursors.remapNode(block, newCandidate);
                newCandidate = createNewCandidate();
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
