import { Plugin } from "../plugin";
import { closestBlock, isBlock } from "../utils/blocks";
import {
    cleanTrailingBR,
    fillEmpty,
    makeContentsInline,
    removeClass,
    removeStyle,
} from "../utils/dom";
import {
    isEmptyBlock,
    isListItemElement,
    isParagraphRelatedElement,
    isSelfClosingElement,
    isEditorTab,
    isPhrasingContent,
    isVisible,
    isEditionBoundary,
    isTextNode,
    isElement,
    isContentEditable,
    isEmpty,
    getDeepestEditablePosition,
} from "../utils/dom_info";
import {
    childNodes,
    children,
    closestElement,
    descendants,
    findUpTo,
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

const IS_MARKER = Symbol("isMarker");
/**
 * Create, position and return an empty text node before which to insert. It
 * will be moved into the document so we can always insert before it. It is
 * flagged as a marker so its mutations can be ignored.
 *
 * @see insertNodes
 *
 * @param {Node} node
 * @param {number} offset
 * @returns { Node & { isMarker: true }}
 */
const createMarkerNode = (node, offset) => {
    const marker = node.ownerDocument.createTextNode("");
    marker[IS_MARKER] = true;
    if (isTextNode(node)) {
        if (offset === 0) {
            node.before(marker);
        } else if (offset === node.length) {
            node.after(marker);
        } else {
            node.splitText(offset).before(marker);
        }
    } else if (isSelfClosingElement(node)) {
        node.before(marker);
    } else {
        node.insertBefore(marker, node.childNodes[offset] || null);
    }
    return marker;
};
const isFragment = (node) => node && node.nodeType === Node.DOCUMENT_FRAGMENT_NODE;

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
 * @typedef {((element: HTMLElement) => boolean | void)[]} can_hold_selection_after_insertion_predicates
 * @typedef {((block: HTMLElement, parent: HTMLElement) => boolean | void)[]} can_insert_block_in_parent_predicates
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
        is_node_removable_predicates: (node) => {
            if (node[IS_MARKER]) {
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
        this.split = this.dependencies.split;
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
     * @param {object} [options]
     * @param {boolean} [options.verbatim = false] if true, insert without processing.
     * @returns {Node[]} the inserted nodes
     */
    insert(content, { verbatim = false } = {}) {
        // Pre-process
        let fragment = this.makeFragment(content);
        if (!verbatim) {
            fragment = this.processThrough("fragment_to_insert_processors", fragment);
        }
        this.dependencies.delete.deleteSelection();
        const nodes = this.processFragmentToInsert(fragment);
        if (!nodes.length) {
            return [];
        }

        // Insert
        const children = nodes.flatMap((item) => (isFragment(item) ? childNodes(item) : item));
        this.trigger("on_will_insert_handlers", children);
        const { focusNode, focusOffset } = this.dependencies.selection.getEditableSelection();
        let insertedContent = this.insertNodesAt(nodes, focusNode, focusOffset);
        insertedContent = this.processThrough("inserted_content_processors", insertedContent);

        // Move selection
        this.moveSelectionAfterInsertion(insertedContent);
        return insertedContent;
    }

    /**
     * Process a fragment before insertion, unwrapping what needs unwrapping,
     * then return a list of nodes to insert (fragments in the case of unwrapped
     * nodes).
     *
     * @see insert
     * @param {DocumentFragment} fragment
     * @returns {(Node|DocumentFragment)[]}
     */
    processFragmentToInsert(fragment) {
        const sel = this.dependencies.selection.getEditableSelection();
        const targetBlock = closestBlock(sel.anchorNode);
        const editableContext = closestElement(sel.focusNode, "[contenteditable=true]");
        const isEditableBlock = isBlock(editableContext);
        const isInEmpty = !isTextNode(sel.focusNode) && isEmpty(sel.focusNode);
        const isSelectionAtStart =
            isInEmpty || (firstLeaf(targetBlock) === sel.anchorNode && sel.anchorOffset === 0);
        const isSelectionAtEnd =
            isInEmpty ||
            (lastLeaf(targetBlock) === sel.focusNode &&
                sel.focusOffset === nodeSize(sel.focusNode));

        const nodes = [];
        const numberOfNodes = fragment.childNodes.length;
        for (const [index, node] of childNodes(fragment).entries()) {
            const wasBlock = isBlock(node);

            // A. Unwrap the first and last blocks if needed.
            const isFirstOrLastBlock = wasBlock && (index === 0 || index === numberOfNodes - 1);
            let shouldUnwrap = false;
            let shouldSkip = false;
            // Empty blocks would disappear if unwrapped.
            if (isFirstOrLastBlock && !isEmptyBlock(node)) {
                const isSelectionAtEdge = index === 0 ? isSelectionAtStart : isSelectionAtEnd;
                shouldUnwrap = this.shouldUnwrapNodeBeforeInsertion(
                    node,
                    targetBlock,
                    numberOfNodes,
                    isSelectionAtEdge
                );
            }
            if (shouldUnwrap) {
                this.processThrough("edge_block_to_unwrap_processors", node, index === 0);
            }
            // B. Unwrap blocks if we're trying to insert in a context that
            // doesn't allow them.
            else if (wasBlock && !isEditableBlock) {
                if (this.split.isUnsplittable(node)) {
                    shouldSkip = true;
                } else {
                    makeContentsInline(node);
                    shouldUnwrap = true;
                }
            }
            if (shouldUnwrap) {
                // Unwrap by replacing the node with a fragment containing its
                // children.
                if (node.childNodes.length) {
                    const fragment = new DocumentFragment();
                    fragment.append(...node.childNodes);
                    nodes.push(fragment);
                }
            } else if (!shouldSkip) {
                nodes.push(node);
            }
        }
        return nodes;
    }

    /**
     * Return true if the given node should be unwrapped before insertion at the
     * given target block, false otherwise.
     *
     * @param {Node} node
     * @param {HTMLElement} targetBlock
     * @param {number} numberOfNodes
     * @param {boolean} isSelectionAtEdge
     * @returns {boolean}
     */
    shouldUnwrapNodeBeforeInsertion(node, targetBlock, numberOfNodes, isSelectionAtEdge) {
        if (
            numberOfNodes === 1 &&
            this.dependencies.baseContainer.isCandidateForBaseContainer(node)
        ) {
            // Inline content may arrive wrapped in a single base container (see
            // `wrapInlinesInBlocks` call in `prepareClipboardData`). In that
            // case the wrapper is not meaningful structure.
            // eg, `p(a[]c) + p(b) = p(ab[]c) ≠ p(a)p(b)p(c)`
            return true;
        }
        if (numberOfNodes > 1 && isSelectionAtEdge) {
            // At the edge of a block, the first inserted block has no left-side
            // content to merge with.
            // eg, `h1([]c) + p(a)p(b) = p(a)h1(bc) ≠ h1(abc)`
            // eg, `h1(a[]) + p(b)p(c) = h1(ab)p(c) ≠ h1(abc)`
            // Both these cases would end up as `h1(a)h1(b)h1(c)` after line
            // break restoration.
            return false;
        }
        if (isEditionBoundary(targetBlock, this.editable)) {
            // A root-anchored selection expresses insertion between top-level
            // children. Using its normalized deep position would invent a
            // reference block and incorrectly merge into that child.
            // eg, `p(a)[] + p(b) = p(a)p(b) ≠ p(ab)`
            return false;
        }
        if (this.split.isUnsplittable(node)) {
            // Don't unwrap an unsplittable block.
            return false;
        }
        if (isEmptyBlock(targetBlock)) {
            // There is no surrounding content to absorb the edge block in an
            // empty reference block, so unwrapping would only erase the pasted
            // block boundary.
            return false;
        }
        if (node.nodeName === targetBlock.nodeName) {
            // Same-tag blocks can merge at the cursor.
            // eg, `p(a[]d) + p(b)div(c) = p(ab)div(c)p(d) ≠ p(a)p(b)div(c)p(d)`
            return true;
        }
        if (targetBlock.nodeName === "DIV" && this.split.isUnsplittable(targetBlock)) {
            // An unsplittable DIV cannot be split around the inserted block.
            // Unwrapping inserts the edge contents without creating a nested
            // block boundary inside the atomic container.
            return true;
        }
        if (
            this.dependencies.baseContainer.isCandidateForBaseContainer(node) &&
            this.dependencies.baseContainer.isCandidateForBaseContainer(targetBlock)
        ) {
            return true;
        }
        return false;
    }

    /**
     * Insert a list of nodes at the given position and return what was
     * inserted. Some of the nodes can be document fragment, to signal that they
     * were previously unwrapped.
     *
     * @see insert
     * @param {(Node | DocumentFragment)[]} nodes
     * @param {Node} targetNode
     * @param {number} targetOffset
     * @returns {Node[]}
     */
    insertNodesAt(nodes, targetNode, targetOffset) {
        const marker = createMarkerNode(targetNode, targetOffset);
        const insertedContent = [];
        for (const [index, item] of nodes.entries()) {
            const previousItem = index > 0 && nodes[index - 1];
            const itemNodes = isFragment(item) ? childNodes(item) : [item];
            for (const [nodeIndex, node] of itemNodes.entries()) {
                if (!nodeIndex && isFragment(previousItem) && !isBlock(item) && isVisible(item)) {
                    // Restore a lost split before an item that was unwrapped.
                    const lineBreaks = this.split.splitBlockNode(...leftPos(marker)).lineBreaks;
                    if (lineBreaks?.length > 1 && isFakeLineBreak(lineBreaks.at(-1))) {
                        // The added fake line break will be made unnecessary by the insertion.
                        lineBreaks.pop().remove();
                    }
                    insertedContent.push(...(lineBreaks || []));
                }
                if (marker.isConnected) {
                    const next = marker.nextSibling;
                    const wasBeforeFakeLineBreak = next?.nodeName === "BR" && isFakeLineBreak(next);
                    const isNodeBlock = isBlock(node);
                    const target = isNodeBlock ? this.getBlockInsertTarget(node, marker) : marker;
                    if (target) {
                        target.before(node);
                        insertedContent.push(node);
                        if (isBlock(target) && isEmptyBlock(target)) {
                            target.before(marker);
                            target.remove();
                        }
                        if (wasBeforeFakeLineBreak && !isNodeBlock) {
                            // Inserting inline content before a fake line break
                            // will make it real. Remove it.
                            next.remove();
                        }
                    }
                }
            }
        }
        marker.remove();

        return insertedContent;
    }

    /**
     * Return the node before which the given block can be inserted, based on
     * the given marker of insertion. In the process, move the the marker or
     * split elements if needed. If we have no way to reach an acceptable
     * position, return `undefined`.
     *
     * @see insertNodes
     * @param {HTMLElement} block
     * @param {Node} marker
     * @returns {Node | undefined} the node before which to insert, if any.
     */
    getBlockInsertTarget(block, marker) {
        // Find the closest ancestor before which it would be possible to insert.
        const canInsert = (parent) =>
            this.checkPredicates("can_insert_block_in_parent_predicates", block, parent) ??
            (isBlock(parent) && !isParagraphRelatedElement(parent));
        const possibleTarget = findUpTo(marker, this.editable, (el) => canInsert(el.parentElement));
        if (possibleTarget === marker) {
            return marker;
        }
        // The marker is at the start of the target -> insert before it.
        if (this.isAtAncestorEdge(marker, possibleTarget, "start")) {
            if (isBlock(possibleTarget)) {
                // We don't move the marker so as not to lose the inline context.
                // eg, `p(i([]d))` + `div(a) p(b) p(c)` = `div(a) p(b) p(i(cd))`
                //                                      ≠ `div(a) p(b) p(ci(d))`
                return possibleTarget;
            }
            // This is a special case where we're inserting a block next to an
            // inline node. Inserting the block means we've left the inline
            // context so we should not continue inserting in that context.
            // eg, `p(a) i([]e)` + `div(b) c div(d)` = `p(a) div(b) c    div(d) i(e)`
            //                                       ≠ `p(a) div(b) i(c) div(d) i(e)`
            possibleTarget.before(marker);
            return marker;
        }
        // The marker is at the end of the target -> insert after it.
        if (this.isAtAncestorEdge(marker, possibleTarget, "end")) {
            // We move the marker because we don't want to keep the inline context.
            possibleTarget.after(marker);
            return marker;
        }
        // Split at the left of the marker up until the target if we can, to
        // insert between the two sides of the split target.
        const parent = possibleTarget.parentElement;
        if (!findUpTo(marker, parent, (el) => isElement(el) && this.split.isUnsplittable(el))) {
            return this.split.splitElementUntil(...leftPos(marker), parent)[1];
        }
    }

    /**
     * Move the selection after insertion.
     *
     * @see insert
     * @param {Node[]} insertedNodes
     */
    moveSelectionAfterInsertion(insertedNodes) {
        if (!insertedNodes.length) {
            return;
        }
        let target = insertedNodes.at(-1);
        const systemNode = this.getResource("system_node_selectors").join(",");
        // TODO AGE: this can probably be simplified further.
        if (isBlock(target)) {
            const leaf = lastLeaf(target, {
                skipFunction: (child) => !isVisible(child) || child.matches?.(systemNode),
            });
            const parent = leaf.parentElement;
            if (
                isContentEditable(parent) &&
                (this.checkPredicates("can_hold_selection_after_insertion_predicates", parent) ??
                    isParagraphRelatedElement(parent))
            ) {
                target = leaf;
            }
        }
        // Set the selection after or at the end of the last inserted node.
        let position = normalizeCursorPosition(...rightPos(target), "right");
        if (isEditionBoundary(position[0], this.editable)) {
            position = getDeepestEditablePosition(...position);
        }
        this.dependencies.selection.setSelection(
            { anchorNode: position[0], anchorOffset: position[1] },
            { normalize: false }
        );
    }

    /**
     * Return true if the given node is at the given edge of its parent, false
     * otherwise.
     *
     * @param {Node} node
     * @param {HTMLElement} ancestor
     * @param {"start"|"end"} edge
     * @returns {boolean}
     */
    isAtAncestorEdge(node, ancestor, edge) {
        while (node !== ancestor) {
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
        this.split.splitBlockSegments();
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
