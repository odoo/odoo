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
    isProtecting,
    isProtected,
    isUnprotecting,
    isContentEditable,
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
import { childNodeIndex, leftPos, nodeSize } from "../utils/position";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import {
    baseContainerGlobalSelector,
    createBaseContainer,
} from "@html_editor/utils/base_container";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { isFakeLineBreak } from "@html_editor/utils/dom_state";

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
 * @typedef {((insertedNodes: Node[]) => void)[]} on_inserted_handlers
 * @typedef {((el: HTMLElement) => void)[]} on_will_set_tag_handlers
 * @typedef {((nodesToInsert: Node[]) => container)[]} on_will_insert_handlers
 *
 * @typedef {((fragment: DocumentFragment) => DocumentFragment)[]} fragment_to_insert_processors
 * @typedef {((nodeToInsert: Node, reference: HTMLElement) => Node)[]} node_to_insert_processors
 * @typedef {((element: HTMLElement, isFirst: boolean) => Element)[]} element_to_isolate_processors
 *
 * @typedef {((parent: HTMLElement, blockToInsert: HTMLElement) => boolean | void)[]} is_parent_compatible_for_insertion_predicates
 * @typedef {((referenceBlock: HTMLElement, blockToInsert: HTMLElement) => boolean | void)[]} is_boundary_insertion_block_mergeable_predicates
 *
 * @typedef {string[]} system_attributes
 * @typedef {string[]} system_classes
 * @typedef {string[]} system_style_properties
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
        clean_for_save_processors: (root) => {
            this.removeEmptyClassAndStyleAttributes(root);
            return root;
        },
        clipboard_content_processors: this.removeEmptyClassAndStyleAttributes.bind(this),
        is_functional_empty_node_predicates: (node) => {
            if (isSelfClosingElement(node) || isEditorTab(node)) {
                return true;
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
     * Wrap inline children nodes in Blocks, optionally updating cursors for
     * later selection restore. A paragraph is used for phrasing node, and a div
     * is used otherwise.
     *
     * @param {HTMLElement} element - block element
     * @param {Cursors} [cursors]
     */
    wrapInlinesInBlocks(
        element,
        { baseContainerNodeName = "P", cursors = { update: () => {} } } = {}
    ) {
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
            return currentBlock;
        };
        const removeNode = (node, cursors) => {
            cursors.update(callbacksForCursorUpdate.remove(node));
            node.remove();
        };

        const children = childNodes(element);
        const visibleNodes = new Set(children.filter(isVisible));

        let currentBlock;
        let shouldBreakLine = true;
        for (const node of children) {
            if (isBlock(node)) {
                shouldBreakLine = true;
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
    }

    /**
     * @param {string | DocumentFragment | Element | null} content
     */
    insert(content) {
        if (!content) {
            return;
        }

        // Delete any selected content before inserting.
        if (!this.dependencies.selection.getEditableSelection().isCollapsed) {
            this.dependencies.delete.deleteSelection();
        }

        // Process the nodes to insert.
        const nodesToInsert = childNodes(
            this.processThrough("fragment_to_insert_processors", this.makeFragment(content))
        );
        if (!nodesToInsert.length) {
            return [];
        }

        // Insert the content.
        this.trigger("on_will_insert_handlers", nodesToInsert);
        let insertedContent = this.insertNodes(nodesToInsert);
        this.trigger("on_inserted_handlers", insertedContent);

        // Clean up trailing line breaks.
        const isCleanable = (node) =>
            !isProtecting(node) &&
            !(isProtected(node) && !isUnprotecting(node)) &&
            node.isContentEditable;
        [...getConnectedParents(insertedContent)].filter(isCleanable).forEach(cleanTrailingBR);

        // Move the selection after the insertion.
        insertedContent = insertedContent.filter((node) => node.isConnected);
        if (insertedContent.length) {
            const predicate = (child) => isPhrasingContainer(child) && isContentEditable(child);
            const lastPhrasingContainer = lastLeaf(insertedContent.at(-1), { predicate });
            if (lastPhrasingContainer) {
                this.dependencies.selection.setCursorEnd(lastPhrasingContainer);
            } else {
                this.dependencies.selection.setSelectionAfter(insertedContent.at(-1));
            }
        }

        return insertedContent;
    }

    /**
     * Return a document fragment with the given content normalized.
     *
     * @param {string | DocumentFragment | Element | null} content
     * @returns {DocumentFragment}
     */
    makeFragment(content) {
        const fragment = this.document.createDocumentFragment();
        if (typeof content === "string") {
            fragment.textContent = content;
        } else {
            if (isElement(content)) {
                this.processThrough("normalize_processors", content);
            } else {
                for (const child of children(content)) {
                    this.processThrough("normalize_processors", child);
                }
            }
            fragment.replaceChildren(content);
        }
        return fragment;
    }

    /**
     * Take a list of nodes to insert and insert them in the DOM at selection.
     * Return the list of inserted nodes.
     *
     * @param {Node[]} nodes
     * @returns {Node[]}
     */
    insertNodes(nodes) {
        // An empty text node may be needed to mark the position of insertion.
        const marker = this.document.createTextNode("");

        // Find the location of insertion.
        const { anchorNode, anchorOffset } = this.dependencies.selection.getEditableSelection();
        let reference = anchorNode;
        if (isTextNode(anchorNode)) {
            if (anchorOffset && anchorOffset === anchorNode.length) {
                anchorNode.after(marker);
                reference = anchorNode.nextSibling;
            } else {
                reference = anchorOffset ? anchorNode.splitText(anchorOffset) : anchorNode;
            }
        } else if (!isSelfClosingElement(anchorNode)) {
            if (!anchorNode.childNodes.length || anchorOffset === anchorNode.childNodes.length) {
                anchorNode.append(marker);
            }
            reference = anchorNode.childNodes[anchorOffset];
        }

        const [last, isOnly] = [nodes.at(-1), nodes.length === 1];
        const insertedContent = [];
        let didUnwrapPreviousBlock = false;
        let node;
        let isFirst = true;
        while ((node = nodes.shift())) {
            const referenceLeaf = firstLeaf(reference);

            // 1. Deal with boundary nodes.
            let didUnwrapBlock;
            if (isFirst || node === last) {
                // A. Process the node.
                // TODO AGE: see if I can do that when setting the selection instead.
                // Empty blocks at the pasted fragment boundaries must contain a BR so
                // the browser can place the cursor inside them after insertion.
                const leaves = [isFirst && firstLeaf(node), node === last && lastLeaf(node)];
                for (const leaf of leaves) {
                    if (
                        isBlock(leaf) &&
                        closestElement(leaf, "[contenteditable]")?.contentEditable !== "false"
                    ) {
                        fillEmpty(leaf);
                    }
                }

                // B. Unwrap if needed.
                if (
                    // In case the html inserted is all contained in a single
                    // root <p> or <li> tag, we take the all content of the <p>
                    // or <li> and avoid inserting the <p> or <li>.
                    (isOnly && this.dependencies.baseContainer.isCandidateForBaseContainer(node)) ||
                    (!(isFirst && !isOnly && this.isAtStartOfBlock(referenceLeaf)) &&
                        this.isBoundaryInsertionNodeMergeable(referenceLeaf, node))
                ) {
                    this.processThrough("element_to_isolate_processors", node, isFirst);
                    didUnwrapBlock = isBlock(node);
                    nodes.unshift(...childNodes(node)); // unwrap
                    node = nodes.shift();
                }
            }

            // 2. Find the next reference to insert.
            reference = this.findNextInsertionReference(node, referenceLeaf, marker);
            if (
                !this.canInsertNodeBefore(node, reference) &&
                this.dependencies.split.isUnsplittable(reference.parentElement)
            ) {
                // Inline the content to insert.
                if (this.dependencies.split.isSplittable(node)) {
                    didUnwrapBlock = isBlock(node);
                    makeContentsInline(node);
                    nodes.unshift(...node.childNodes);
                }
                node = nodes.shift();
            }

            // 3. Process the node and insert it.
            if (node) {
                node = this.processThrough("node_to_insert_processors", node, reference);
                const wasFakeLineBreak = reference.nodeName === "BR" && isFakeLineBreak(reference);
                reference.before(node);
                insertedContent.push(node);

                // 4. Deal with consecutive unwrapped blocks.
                if (didUnwrapBlock && didUnwrapPreviousBlock) {
                    // We inserted two elements that we had to unwrap, but we
                    // want to preserve the newline between them, so we split.
                    if (!node.nextSibling) {
                        node.after(marker);
                    }
                    reference = node.nextSibling;
                    const [targetNode, targetOffset] = leftPos(node);
                    this.dependencies.split.splitBlockNode({ targetNode, targetOffset });
                }

                // 5. Clean up: remove the reference if needed.
                if (
                    // A. Inserting a phrasing container (even nested) in an
                    // empty block should mean replacing that block.
                    (isFirst && isEmptyBlock(reference) && findDownTo(node, isPhrasingContainer)) ||
                    // B. Inserting inline content before a fake line break will
                    // make it real. Remove it.
                    (wasFakeLineBreak && !isBlock(node))
                ) {
                    reference.remove();
                    // Reset the reference if needed.
                    if (nodes.length) {
                        node = node.isConnected ? node : parent;
                        node.after(marker);
                        reference = node.nextSibling;
                    }
                }
            }
            if (didUnwrapBlock) {
                didUnwrapPreviousBlock = true;
            } else if (isBlock(node)) {
                didUnwrapPreviousBlock = false;
            }
            isFirst = false;
        }
        // Remove the marker we may have inserted to help with insertion.
        marker.remove();
        return insertedContent;
    }

    findNextInsertionReference(node, reference, marker) {
        if (
            !isTextNode(reference) &&
            !isSelfClosingElement(reference) &&
            !reference.childNodes.length
        ) {
            node.append(marker);
            reference = node.firstChild;
        }
        let parent = reference.parentElement;
        if (this.canInsertNodeBefore(node, reference) || isEditionBoundary(parent, this.editable)) {
            return reference;
        }
        if (this.isAtStartOfBlock(reference)) {
            return this.findNextInsertionReference(node, parent, marker);
        }
        if (nodeSize(reference) === 0 && this.isAtEndOfBlock(reference)) {
            // Will have to be removed later.
            parent.after(marker);
            return this.findNextInsertionReference(node, parent.nextSibling, marker);
        }
        if (this.dependencies.split.isSplittable(parent)) {
            this.dependencies.split.splitElement(parent, childNodeIndex(reference));
            // The reference shouldn't have changed, it just moved into a new parent.
            parent = reference.parentElement;
            return this.findNextInsertionReference(
                node,
                isBlock(parent) ? reference : parent,
                marker
            );
        }
        return reference;
    }

    isAtStartOfBlock(node) {
        const parentBlock = closestBlock(node);
        while (node !== parentBlock) {
            if (childNodeIndex(node) !== 0) {
                return false;
            }
            node = node.parentElement;
        }
        return true;
    }

    isAtEndOfBlock(node) {
        const parentBlock = closestBlock(node);
        while (node !== parentBlock) {
            if (childNodeIndex(node) !== nodeSize(node.parentElement) - 1) {
                return false;
            }
            node = node.parentElement;
        }
        return true;
    }
    isBoundaryInsertionNodeMergeable(reference, node) {
        if (!isBlock(node) || isEmptyBlock(node) || this.dependencies.split.isUnsplittable(node)) {
            return false;
        }
        const referenceBlock = closestBlock(reference);
        if (isEmptyBlock(referenceBlock) || isEditionBoundary(referenceBlock, this.editable)) {
            return false;
        }
        if (
            node.nodeName === referenceBlock.nodeName ||
            (referenceBlock.nodeName === "DIV" &&
                this.dependencies.split.isUnsplittable(referenceBlock))
        ) {
            return true;
        }
        return (
            this.checkPredicates(
                "is_boundary_insertion_block_mergeable_predicates",
                referenceBlock,
                node
            ) ?? false
        );
    }

    canInsertNodeBefore(node, reference) {
        if (!isBlock(node)) {
            return true;
        }
        const parent = reference.parentElement;
        return (
            allowsParagraphRelatedElements(parent) &&
            (this.checkPredicates("is_parent_compatible_for_insertion_predicates", parent, node) ??
                true)
        );
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
