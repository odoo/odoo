import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import {
    cleanTrailingBR,
    fillEmpty,
    makeContentsInline,
    removeClass,
    removeStyle,
    unwrapContents,
} from "../utils/dom";
import {
    allowsParagraphRelatedElements,
    isEmptyBlock,
    isListItemElement,
    isParagraphRelatedElement,
    isSelfClosingElement,
    isEditorTab,
    isPhrasingContent,
    isVisible,
    isEditionBoundary,
    isPhrasingContainer,
    isTextNode,
    isElement,
    isContentEditable,
    getDeepestEditablePosition,
    isEmpty,
} from "../utils/dom_info";
import {
    childNodes,
    children,
    closestElement,
    descendants,
    findDownTo,
    firstLeaf,
    getConnectedParents,
    lastLeaf,
} from "../utils/dom_traversal";
import { FONT_SIZE_CLASSES, TEXT_STYLE_CLASSES } from "../utils/formatting";
import { childNodeIndex, nodeSize, leftPos, rightPos } from "../utils/position";
import { callbacksForCursorUpdate, normalizeCursorPosition } from "@html_editor/utils/selection";
import {
    baseContainerGlobalSelector,
    createBaseContainer,
} from "@html_editor/utils/base_container";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { isFakeLineBreak } from "@html_editor/utils/dom_state";
import { NATIVE_MUTATION_TYPES } from "./dom_observer_plugin";
import { SPLIT_OPERATION_TYPES } from "./split_plugin";

const IS_MARKER = Symbol("isMarker");
/**
 * Creates and returns an empty text node that may be needed to mark the
 * position of insertion. It is flagged as a marker so its mutations can be
 * ignored.
 *
 * @param {HTMLDocument} doc
 * @returns { Node & { isMarker: true }}
 */
const createMarkerNode = (doc) => {
    const marker = doc.createTextNode("");
    marker[IS_MARKER] = true;
    return marker;
};
/**
 * Helper for { @see insert }. Take a selection point and return a node at its
 * deepest position, inserting the given marker if needed.
 *
 * @param {{ anchorNode: Node, anchorOffset: number }} selectionPoint
 * @param {Node} marker
 * @returns { Node }
 */
const findInsertionReferenceNode = ({ anchorNode: node, anchorOffset: offset }, marker) => {
    if (isTextNode(node)) {
        if (offset && offset === node.length) {
            node.after(marker);
            return node.nextSibling;
        }
        return offset ? node.splitText(offset) : node;
    }
    if (!isSelfClosingElement(node)) {
        if (!node.childNodes.length || offset === node.childNodes.length) {
            node.append(marker);
        }
        return node.childNodes[offset];
    }
    return node;
};

/**
 * @typedef {Object} DomShared
 * @property { DomPlugin['normalize'] } normalize
 * @property { DomPlugin['insert'] } insert
 * @property { DomPlugin['copyAttributes'] } copyAttributes
 * @property { DomPlugin['canSetBlock'] } canSetBlock
 * @property { DomPlugin['setBlock'] } setBlock
 * @property { DomPlugin['setTagName'] } setTagName
 * @property { DomPlugin['removeSystemProperties'] } removeSystemProperties
 * @property { DomPlugin['wrapInlinesInBlocks'] } wrapInlinesInBlocks
 */

/**
 * @typedef {((el: HTMLElement) => void)[]} on_will_set_tag_handlers
 * @typedef {((root: HTMLElement) => void)[]} on_will_normalize_handlers
 * @typedef {((root: HTMLElement) => void)[]} on_normalized_handlers
 * @typedef {((nodesToInsert: Node[]) => container)[]} on_will_insert_handlers
 *
 * @typedef {((root: EditorContext["editable"] | HTMLElement) => EditorContext["editable"] | HTMLElement)[]} normalize_processors
 * @typedef {((fragment: DocumentFragment) => DocumentFragment)[]} fragment_to_insert_processors
 * @typedef {((element: HTMLElement, isFirst: boolean) => Element)[]} edge_block_to_unwrap_processors
 * @typedef {((insertedNodes: Node[]) => void)[]} inserted_content_processors
 *
 * @typedef {((parent: HTMLElement, blockToInsert: HTMLElement) => boolean | void)[]} is_parent_compatible_for_insertion_predicates
 * @typedef {((element: HTMLElement) => boolean | void)[]} can_hold_selection_after_insertion_predicates
 *
 * @typedef {string[]} system_attributes
 * @typedef {string[]} system_classes
 * @typedef {string[]} system_style_properties
 */

export class DomPlugin extends Plugin {
    static id = "dom";
    static dependencies = ["baseContainer", "selection", "history", "split", "delete", "lineBreak"];
    static shared = [
        "normalize",
        "insert",
        "copyAttributes",
        "canSetBlock",
        "setBlock",
        "setTagName",
        "removeSystemProperties",
        "wrapInlinesInBlocks",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "setTag",
                run: this.setBlock.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        /** Handlers */
        on_editor_started_handlers: withSequence(0, this.normalize.bind(this)),
        /** Processors */
        inserted_content_processors: (insertedContent) => {
            // Remove trailing line breaks.
            getConnectedParents(insertedContent).forEach(cleanTrailingBR);
            insertedContent = insertedContent.filter((node) => node.isConnected);
            // Empty blocks at the inserted edges must contain a BR so the browser
            // can place the cursor inside them after insertion.
            const shouldFillEmpty = (node) =>
                isBlock(node) && this.dependencies.selection.isNodeEditable(node);
            [firstLeaf(insertedContent[0]), lastLeaf(insertedContent.at(-1))]
                .filter(shouldFillEmpty)
                .forEach(fillEmpty);
            return insertedContent;
        },
        clean_for_save_processors: (root) => {
            this.removeEmptyClassAndStyleAttributes(root);
            return root;
        },
        clipboard_content_processors: this.removeEmptyClassAndStyleAttributes.bind(this),
        fragment_to_insert_processors: withSequence(Infinity, (fragment) => {
            const nodes = childNodes(fragment);
            const sel = this.dependencies.selection.getEditableSelection();
            const refBlock = closestBlock(sel.anchorNode);
            const editableContext = closestElement(sel.focusNode, "[contenteditable=true]");
            const isEditableBlock = isBlock(editableContext);
            const doesEditableAllowParagraphRelatedElements =
                allowsParagraphRelatedElements(editableContext);
            const isInEmpty = !isTextNode(sel.focusNode) && isEmpty(sel.focusNode);
            const isSelectionAtStart =
                isInEmpty || (firstLeaf(refBlock) === sel.anchorNode && sel.anchorOffset === 0);
            const isSelectionAtEnd =
                isInEmpty ||
                (lastLeaf(refBlock) === sel.focusNode &&
                    sel.focusOffset === nodeSize(sel.focusNode));

            let previousWasBlock = false;
            let previousDidUnwrap = false;
            this.nodesBeforeWhichToRestoreLineBreak = new Set();
            for (const [index, node] of nodes.entries()) {
                const wasBlock = isBlock(node);
                const isSelectionAtEdge = index === 0 ? isSelectionAtStart : isSelectionAtEnd;
                let didUnwrap = false;
                let firstResultNode = node;

                // A. Unwrap the first and last blocks if needed.
                const isFirstOrLastBlock = wasBlock && (index === 0 || index === nodes.length - 1);
                let shouldUnwrap = false;
                // Empty blocks would disappear if unwrapped.
                if (isFirstOrLastBlock && !isEmptyBlock(node)) {
                    if (
                        nodes.length === 1 &&
                        this.dependencies.baseContainer.isCandidateForBaseContainer(node)
                    ) {
                        // Inline content may arrive wrapped in a single base
                        // container (see `wrapInlinesInBlocks` call in
                        // `prepareClipboardData`). In that case the wrapper is
                        // not meaningful structure.
                        // eg, `p(a[]c) + p(b) = p(ab[]c) ≠ p(a)p(b)p(c)`
                        shouldUnwrap = true;
                    } else if (nodes.length > 1 && isSelectionAtEdge) {
                        // At the edge of a block, the first inserted block has
                        // no left-side content to merge with.
                        // eg, `h1([]c) + p(a)p(b) = p(a)h1(bc) ≠ h1(abc)`
                        // eg, `h1(a[]) + p(b)p(c) = h1(ab)p(c) ≠ h1(abc)`
                        // Both these cases would end up as `h1(a)h1(b)h1(c)`
                        // after line break restoration.
                        shouldUnwrap = false;
                    } else if (isEditionBoundary(refBlock, this.editable)) {
                        // A root-anchored selection expresses insertion between
                        // top-level children. Using its normalized deep
                        // position would invent a reference block and
                        // incorrectly merge into that child.
                        // eg, `p(a)[] + p(b) = p(a)p(b) ≠ p(ab)`
                        shouldUnwrap = false;
                    } else if (this.dependencies.split.isUnsplittable(node)) {
                        // Don't unwrap an unsplittable block.
                        shouldUnwrap = false;
                    } else if (isEmptyBlock(refBlock)) {
                        // There is no surrounding content to absorb the edge
                        // block in an empty reference block, so unwrapping
                        // would only erase the pasted block boundary.
                        shouldUnwrap = false;
                    } else if (node.nodeName === refBlock.nodeName) {
                        // Same-tag blocks can merge at the cursor.
                        // eg, `p(a[]d) + p(b)div(c) = p(ab)div(c)p(d) ≠ p(a)p(b)div(c)p(d)`
                        shouldUnwrap = true;
                    } else if (
                        refBlock.nodeName === "DIV" &&
                        this.dependencies.split.isUnsplittable(refBlock)
                    ) {
                        // An unsplittable DIV cannot be split around the
                        // inserted block. Unwrapping inserts the edge contents
                        // without creating a nested block boundary inside the
                        // atomic container.
                        shouldUnwrap = true;
                    } else if (
                        this.dependencies.baseContainer.isCandidateForBaseContainer(node) &&
                        this.dependencies.baseContainer.isCandidateForBaseContainer(refBlock)
                    ) {
                        shouldUnwrap = true;
                    }
                }
                if (shouldUnwrap) {
                    this.processThrough("edge_block_to_unwrap_processors", node, index === 0);
                    firstResultNode = node.firstChild;
                    unwrapContents(node);
                    didUnwrap = true;
                }
                // B. Unwrap blocks if we're trying to insert in a context that
                // doesn't allow them.
                else if (
                    wasBlock &&
                    !isEditableBlock &&
                    !doesEditableAllowParagraphRelatedElements
                ) {
                    if (this.dependencies.split.isUnsplittable(node)) {
                        node.remove();
                        firstResultNode = undefined;
                    } else {
                        makeContentsInline(node);
                        firstResultNode = node.firstChild;
                        unwrapContents(node);
                        didUnwrap = true;
                    }
                }

                // C. Mark the first surviving node after an erased block boundary.
                const didLoseLineBreak =
                    index > 0 &&
                    ((didUnwrap && (previousDidUnwrap || !previousWasBlock)) ||
                        (previousDidUnwrap && !wasBlock));
                if (didLoseLineBreak && firstResultNode) {
                    this.nodesBeforeWhichToRestoreLineBreak.add(firstResultNode);
                }

                previousWasBlock = wasBlock;
                previousDidUnwrap = didUnwrap;
            }
            return fragment;
        }),
        /** Predicates */
        is_functional_empty_node_predicates: (node) => {
            if (isSelfClosingElement(node) || isEditorTab(node)) {
                return true;
            }
        },
        is_mutation_savable_predicates: (mutation) => {
            if (
                mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST &&
                [...mutation.addedNodes, ...mutation.removedNodes].every((node) => node[IS_MARKER])
            ) {
                return false;
            }
        },
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
     * Normalize the contents of the given root element (or the editable if none
     * was given).
     *
     * @param {HTMLElement} [root = this.editable]
     */
    normalize(root = this.editable) {
        this.trigger("on_will_normalize_handlers", root);
        this.processThrough("normalize_processors", root);
        this.trigger("on_normalized_handlers", root);
    }

    /**
     * Wrap inline children nodes in blocks, optionally updating cursors for
     * later selection restore. A paragraph is used for phrasing node, and a div
     * is used otherwise.
     *
     * @param {HTMLElement} element - block element
     * @param {Cursors} [cursors]
     * @returns {Map<Node, Node|null>} a map of the nodes handled to their
     *                                 resulting block, themselves if nothing
     *                                 was done, or null if they were removed.
     */
    wrapInlinesInBlocks(
        element,
        { baseContainerNodeName = "P", cursors = { update: () => {} } } = {}
    ) {
        const nodesToResults = new Map();
        // Helpers to manipulate preserving selection.
        const wrapInBlock = (node, cursors) => {
            const nextSibling = node.nextSibling;
            const parent = node.parentElement;
            let block;
            if (isPhrasingContent(node)) {
                block = createBaseContainer(baseContainerNodeName, node.ownerDocument, [node]);
            } else {
                block = node.ownerDocument.createElement("DIV");
                node.remove();
                block.append(node);
            }
            cursors.update(callbacksForCursorUpdate.append(block, node));
            cursors.update(callbacksForCursorUpdate.before(node, block));
            nextSibling ? nextSibling.before(block) : parent.append(block);
            nodesToResults.set(node, block);
            return block;
        };
        const appendToCurrentBlock = (currentBlock, node, cursors) => {
            if (currentBlock.matches(baseContainerGlobalSelector) && !isPhrasingContent(node)) {
                const block = currentBlock.ownerDocument.createElement("DIV");
                cursors.update(callbacksForCursorUpdate.before(currentBlock, block));
                currentBlock.before(block);
                for (const child of childNodes(currentBlock)) {
                    cursors.update(callbacksForCursorUpdate.append(block, child));
                    block.append(child);
                }
                cursors.update(callbacksForCursorUpdate.remove(currentBlock));
                currentBlock.remove();
                currentBlock = block;
            }
            cursors.update(callbacksForCursorUpdate.append(currentBlock, node));
            currentBlock.append(node);
            nodesToResults.set(node, currentBlock);
            return currentBlock;
        };
        const removeNode = (node, cursors) => {
            cursors.update(callbacksForCursorUpdate.remove(node));
            node.remove();
            nodesToResults.set(node, null);
        };

        const children = childNodes(element);
        const visibleNodes = new Set(children.filter(isVisible));

        let currentBlock;
        let shouldBreakLine = true;
        for (const node of children) {
            if (isBlock(node)) {
                shouldBreakLine = true;
                nodesToResults.set(node, node);
            } else if (
                !visibleNodes.has(node) &&
                (this.checkPredicates("is_node_removable_predicates", node) ?? true)
            ) {
                removeNode(node, cursors);
            } else if (node.nodeName === "BR") {
                if (shouldBreakLine) {
                    wrapInBlock(node, cursors);
                } else {
                    // BR preceded by inline content: discard it and make sure
                    // next inline goes in a new Block
                    removeNode(node, cursors);
                    shouldBreakLine = true;
                }
            } else if (shouldBreakLine) {
                currentBlock = wrapInBlock(node, cursors);
                shouldBreakLine = false;
            } else {
                currentBlock = appendToCurrentBlock(currentBlock, node, cursors);
            }
        }
        return nodesToResults;
    }

    /**
     * @param {string | DocumentFragment | Element | null} content
     * @returns {Node[]} the inserted nodes
     */
    insert(content) {
        this.dependencies.delete.deleteSelection();

        // 1. Process the content to insert.
        // =================================

        const nodes = childNodes(
            this.processThrough("fragment_to_insert_processors", this.makeFragment(content))
        );
        if (!nodes.length) {
            return [];
        }

        // 2. Insert the content.
        // ======================

        this.trigger("on_will_insert_handlers", nodes);

        // An empty text node may be needed to mark the position of insertion.
        const marker = createMarkerNode(this.document);
        // Find the first insertion reference (the node before which to insert).
        let refNode = findInsertionReferenceNode(
            this.dependencies.selection.getEditableSelection(),
            marker
        );

        // Insert the nodes.
        let insertedContent = [];
        const firstNode = nodes[0];
        for (const node of nodes) {
            const next = this.findNextInsertionReferenceNode(node, firstLeaf(refNode), marker);
            if (next) {
                refNode = next;
                const wasFakeLineBreak = refNode.nodeName === "BR" && isFakeLineBreak(refNode);
                refNode.before(node);
                insertedContent.push(node);
                const shouldRemoveReference =
                    // Inserting a phrasing container (even nested) in an empty
                    // block should mean replacing that block.
                    (node === firstNode &&
                        isEmptyBlock(refNode) &&
                        findDownTo(node, isPhrasingContainer)) ||
                    // Inserting inline content before a fake line break will
                    // make it real. Remove it.
                    (wasFakeLineBreak && !isBlock(node));
                if (shouldRemoveReference) {
                    refNode.remove();
                    node.after(marker);
                    refNode = marker;
                }
            }
        }
        marker.remove();

        // Restore lost breaks.
        for (const node of this.nodesBeforeWhichToRestoreLineBreak) {
            const index = insertedContent.indexOf(node);
            if (index === -1 || !node.parentNode) {
                continue;
            }
            const [targetNode, targetOffset] = leftPos(node);
            const split = this.dependencies.split.splitBlockNode({ targetNode, targetOffset });
            switch (split.type) {
                case SPLIT_OPERATION_TYPES.LINE: {
                    insertedContent.splice(index, 1, ...split.lineBreaks, node);
                    break;
                }
                case SPLIT_OPERATION_TYPES.BLOCK: {
                    if (!node.isConnected) {
                        insertedContent.splice(index, 1);
                        split.after.remove();
                    } else if (this.isAtBlockEdge(node, "end")) {
                        insertedContent.splice(index, 1, split.after);
                    }
                    break;
                }
                default: {
                    if (this.isAtBlockEdge(node, "end")) {
                        insertedContent.splice(index, 1, closestBlock(node));
                    }
                }
            }
        }

        insertedContent = this.processThrough("inserted_content_processors", insertedContent);

        // 3. Move the selection after the insertion.
        // ==========================================

        const lastNode = insertedContent.at(-1);
        const elementToEnter = lastNode && this.findElementToEnterAfterInsert(lastNode);
        if (elementToEnter) {
            this.dependencies.selection.setCursorEnd(elementToEnter);
        } else if (lastNode) {
            // Set the selection after the last inserted node.
            let position = rightPos(lastNode);
            position = normalizeCursorPosition(position[0], position[1], "right");
            if (!this.config.allowInlineAtRoot && isEditionBoundary(position[0], this.editable)) {
                // Correct the position if it happens to be in the editable root.
                position = getDeepestEditablePosition(...position);
            }
            this.dependencies.selection.setSelection(
                { anchorNode: position[0], anchorOffset: position[1] },
                { normalize: false }
            );
        }

        return insertedContent;
    }

    /**
     * Take a node to insert and the last valid reference leaf for its
     * insertion, adapt the reference for the next insertion, and return it.
     *
     * @param {Node} node
     * @param {Node} reference
     * @param {Node} marker
     * @returns {Node | undefined}
     */
    findNextInsertionReferenceNode(node, reference, marker) {
        const parent = reference.parentElement;
        const checkPredicates = () =>
            this.checkPredicates("is_parent_compatible_for_insertion_predicates", parent, node);
        if (
            !isBlock(node) ||
            (allowsParagraphRelatedElements(parent) && (checkPredicates() ?? true)) ||
            isEditionBoundary(parent, this.editable)
        ) {
            return reference;
        }
        if (this.isAtBlockEdge(reference, "start")) {
            return this.findNextInsertionReferenceNode(node, parent, marker);
        }
        if (
            (!nodeSize(reference) || !isVisible(reference)) &&
            this.isAtBlockEdge(reference, "end")
        ) {
            parent.after(marker);
            return this.findNextInsertionReferenceNode(node, marker, marker);
        }
        if (!this.dependencies.split.isUnsplittable(parent)) {
            this.dependencies.split.splitElement(parent, childNodeIndex(reference));
            // The reference shouldn't have changed, it just moved into a new parent.
            const newParent = reference.parentElement;
            const nextReference = isBlock(newParent) ? reference : newParent;
            return this.findNextInsertionReferenceNode(node, nextReference, marker);
        }
    }

    /**
     * Return true if the given node is at the given edge of its closest
     * block, false otherwise.
     *
     * @param {Node} node
     * @param {"start"|"end"} edge
     * @returns {boolean}
     */
    isAtBlockEdge(node, edge) {
        const parentBlock = closestBlock(node);
        while (node !== parentBlock) {
            const index = childNodeIndex(node);
            const parent = node.parentElement;
            // Search for the first/last visible child.
            let visibleChild = parent[`${edge === "start" ? "first" : "last"}Child`];
            while (visibleChild && !isVisible(visibleChild)) {
                visibleChild = visibleChild[`${edge === "start" ? "next" : "previous"}Sibling`];
            }
            if (visibleChild) {
                const visibleIndex = childNodeIndex(visibleChild);
                if (edge === "start" ? index > visibleIndex : index < visibleIndex) {
                    return false;
                }
            }
            node = parent;
        }
        return true;
    }

    /**
     * @param {string | DocumentFragment | Element | null} content
     * @returns {DocumentFragment}
     */
    makeFragment(content) {
        const fragment = this.document.createDocumentFragment();
        if (typeof content === "string") {
            fragment.textContent = content;
        } else if (content) {
            (isElement(content) ? [content] : children(content)).forEach(this.normalize.bind(this));
            fragment.replaceChildren(content);
        }
        return fragment;
    }

    /**
     * Take the last node inserted using @see insert and return its child at the
     * end of which to put the selection, if any.
     *
     * @param {Node} node
     * @returns {Node | undefined}
     */
    findElementToEnterAfterInsert(node) {
        const systemNode = this.getResource("system_node_selectors").join(",");
        const candidate = lastLeaf(node, {
            predicate: (child) => !isSelfClosingElement(child) && !isTextNode(child),
            skipFunction: (child) => !isVisible(child) || child.matches?.(systemNode),
        });
        const predicates = "can_hold_selection_after_insertion_predicates";
        if (
            isContentEditable(candidate) &&
            (this.checkPredicates(predicates, candidate) ?? isParagraphRelatedElement(candidate))
        ) {
            return candidate;
        }
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
            this.copyAttributes(el, newEl);
            newEl.replaceChildren(...content);
            el.replaceWith(newEl);
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

    /**
     * Determines if a block element can be safely retagged.
     *
     * Certain blocks (like 'o_savable') should not be retagged because doing so
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
            this.dependencies.delete.isUnremovable(block)
        );
    }

    getBlocksToSet() {
        const isCollapsed = this.dependencies.selection.getEditableSelection().isCollapsed;
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const lastTargetedNode = targetedNodes.slice(-1)[0];
        const targetedBlocks = [...new Set(targetedNodes.map(closestBlock).filter(Boolean))];
        return targetedBlocks.filter(
            (block) =>
                // If the selection ends in a block, the block is not visibly
                // selected so exclude it.
                (isCollapsed || block !== lastTargetedNode) &&
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
        const createNewCandidate = () => {
            let newCandidate = this.document.createElement(tagName.toUpperCase());
            if (extraClass) {
                newCandidate.classList.add(extraClass);
            }
            if (this.dependencies.baseContainer.isCandidateForBaseContainer(newCandidate)) {
                const baseContainer = this.dependencies.baseContainer.createBaseContainer({
                    nodeName: newCandidate.nodeName,
                });
                this.copyAttributes(newCandidate, baseContainer);
                newCandidate = baseContainer;
            }
            return newCandidate;
        };
        let newCandidate = createNewCandidate();
        this.dependencies.split.splitBlockSegments();
        const cursors = this.dependencies.selection.preserveSelection();
        let newEl;
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
                const params = { block, newEl, tagName, cursors };
                this.trigger("on_will_set_tag_handlers", params);
                if (this.delegateTo("set_block_overrides", params)) {
                    continue;
                }
                newEl = this.setTagName(params.block, tagName);
                cursors.remapNode(params.block, newEl);
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
                newCandidate.replaceChildren(...childNodes(block));
                block.append(newCandidate);
                cursors.remapNode(block, newCandidate);
                newCandidate = createNewCandidate();
            }
        }
        cursors.restore();
        this.dependencies.history.commit();
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
        return root;
    }
}
