import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { unwrapContents } from "@html_editor/utils/dom";
import {
    isParagraphRelatedElement,
    isRedundantElement,
    isEmptyBlock,
    isVisibleTextNode,
    isStylable,
    isContentEditableAncestor,
} from "@html_editor/utils/dom_info";
import {
    ancestors,
    childNodes,
    closestElement,
    descendants,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { FontTypeSelector } from "./font_type_selector";
import {
    getBaseContainerSelector,
    SUPPORTED_BASE_CONTAINER_NAMES,
} from "@html_editor/utils/base_container";
import { READ, withSequence } from "@html_editor/utils/resource";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { weakMemoize } from "@html_editor/utils/functions";

/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */

/**
 * @typedef {((insertedNode: Node) => insertedNode)[]} before_insert_within_pre_processors
 * @typedef {{ name: LazyTranslatedString; tagName: string; extraClass?: string; }[]} font_type_items
 */

const headingTags = ["H1", "H2", "H3", "H4", "H5", "H6"];
const handledElemSelector = [...headingTags, "BLOCKQUOTE"].join(", ");

export class FontTypePlugin extends Plugin {
    static id = "fontType";
    static dependencies = [
        "baseContainer",
        "input",
        "split",
        "selection",
        "dom",
        "format",
        "lineBreak",
        "delete",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        font_type_items: [
            withSequence(10, {
                name: _t("Header 1 Display 1"),
                tagName: "h1",
                extraClass: "display-1",
            }),
            ...[
                { name: _t("Header 1"), tagName: "h1" },
                { name: _t("Header 2"), tagName: "h2" },
                { name: _t("Header 3"), tagName: "h3" },
                { name: _t("Header 4"), tagName: "h4" },
                { name: _t("Header 5"), tagName: "h5" },
                { name: _t("Header 6"), tagName: "h6" },
            ].map((item) => withSequence(20, item)),
            withSequence(30, {
                name: _t("Normal"),
                tagName: "div",
                // for the FontTypeSelector component
                selector: getBaseContainerSelector("DIV"),
            }),
            withSequence(40, { name: _t("Paragraph"), tagName: "p" }),
            withSequence(60, { name: _t("Quote"), tagName: "blockquote" }),
        ],
        user_commands: [
            {
                id: "setTagHeading",
                icon: "fa-header",
                run: ({ level } = {}) =>
                    this.dependencies.dom.setBlock({ tagName: `H${level ?? 1}` }),
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
            {
                id: "setTagParagraph",
                title: _t("Text"),
                description: _t("Paragraph block"),
                icon: "fa-paragraph",
                run: () => {
                    this.dependencies.dom.setBlock({
                        tagName: this.dependencies.baseContainer.getDefaultNodeName(),
                    });
                },
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
            {
                id: "setTagQuote",
                title: _t("Quote"),
                description: _t("Add a blockquote section"),
                icon: "fa-quote-right",
                run: () => this.dependencies.dom.setBlock({ tagName: "blockquote" }),
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
        ],
        toolbar_groups: [
            withSequence(10, {
                id: "font",
            }),
        ],
        toolbar_items: [
            withSequence(10, {
                id: "font-type",
                groupId: "font",
                namespaces: ["compact", "expanded"],
                description: _t("Select font style"),
                Component: FontTypeSelector,
                props: {
                    getItems: () => this.availableFontTypeItems,
                    getDisplay: () => this.fontType,
                    onSelected: (item) => {
                        this.dependencies.dom.setBlock({
                            tagName: item.tagName,
                            extraClass: item.extraClass,
                        });
                        this.updateFontTypeSelectorParams();
                    },
                },
                isAvailable: this.blockFormatIsAvailable.bind(this),
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            }),
        ],
        powerbox_categories: withSequence(5, { id: "format", name: _t("Format") }),
        powerbox_items: [
            {
                title: _t("Heading 1"),
                description: _t("Big section heading"),
                categoryId: "format",
                commandId: "setTagHeading",
                commandParams: { level: 1 },
                keywords: [_t("title")],
            },
            {
                title: _t("Heading 2"),
                description: _t("Medium section heading"),
                categoryId: "format",
                commandId: "setTagHeading",
                commandParams: { level: 2 },
                keywords: [_t("title")],
            },
            {
                title: _t("Heading 3"),
                description: _t("Small section heading"),
                categoryId: "format",
                commandId: "setTagHeading",
                commandParams: { level: 3 },
                keywords: [_t("title")],
            },
            {
                categoryId: "format",
                commandId: "setTagParagraph",
            },
            {
                categoryId: "format",
                commandId: "setTagQuote",
            },
        ],
        shorthands: [
            {
                literals: ["#"],
                commandId: "setTagHeading",
                commandParams: { level: 1 },
            },
            {
                literals: ["##"],
                commandId: "setTagHeading",
                commandParams: { level: 2 },
            },
            {
                literals: ["###"],
                commandId: "setTagHeading",
                commandParams: { level: 3 },
            },
            {
                literals: ["####"],
                commandId: "setTagHeading",
                commandParams: { level: 4 },
            },
            {
                literals: ["#####"],
                commandId: "setTagHeading",
                commandParams: { level: 5 },
            },
            {
                literals: ["######"],
                commandId: "setTagHeading",
                commandParams: { level: 6 },
            },
            {
                literals: [">"],
                commandId: "setTagQuote",
            },
        ],
        hints: [
            { selector: "H1", text: _t("Heading 1") },
            { selector: "H2", text: _t("Heading 2") },
            { selector: "H3", text: _t("Heading 3") },
            { selector: "H4", text: _t("Heading 4") },
            { selector: "H5", text: _t("Heading 5") },
            { selector: "H6", text: _t("Heading 6") },
            { selector: "BLOCKQUOTE", text: _t("Quote") },
        ],

        /** Handlers */
        on_selectionchange_handlers: withSequence(
            READ,
            this.updateFontTypeSelectorParams.bind(this)
        ),
        on_undone_handlers: this.updateFontTypeSelectorParams.bind(this),
        on_redone_handlers: this.updateFontTypeSelectorParams.bind(this),
        normalize_processors: this.normalize.bind(this),

        /** Overrides */
        split_element_block_overrides: [
            this.handleSplitBlockHeading.bind(this),
            this.handleSplitBlockquote.bind(this),
        ],
        delete_backward_overrides: withSequence(20, this.handleDeleteBackward.bind(this)),
        delete_backward_word_overrides: this.handleDeleteBackward.bind(this),

        /** Processors */
        clipboard_content_processors: this.processContentForClipboard.bind(this),
    };

    setup() {
        this.fontType = reactive({ displayName: "" });
        this.blockFormatIsAvailableMemoized = weakMemoize(
            (selection) => isHtmlContentSupported(selection) && this.dependencies.dom.canSetBlock()
        );
        this.availableFontTypeItems = this.getResource("font_type_items").filter(
            ({ tagName }) =>
                !SUPPORTED_BASE_CONTAINER_NAMES.includes(tagName.toUpperCase()) ||
                this.config.baseContainers.includes(tagName.toUpperCase())
        );
    }

    normalize(root) {
        for (const el of selectElements(
            root,
            "strong, b, span[style*='font-weight: bolder'], small"
        )) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
    }

    get fontTypeName() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        // if (!sel) {
        //     return "Normal";
        // }
        const anchorNode = sel.anchorNode;
        const block = closestBlock(anchorNode);
        const tagName = block.tagName.toLowerCase();

        const matchingItems = this.availableFontTypeItems.filter((item) =>
            item.selector ? block.matches(item.selector) : item.tagName === tagName
        );

        const matchingItemsWithoutExtraClass = matchingItems.filter((item) => !item.extraClass);

        if (!matchingItems.length) {
            return _t("Normal");
        }

        return (
            matchingItems.find((item) => block.classList.contains(item.extraClass)) ||
            (matchingItemsWithoutExtraClass.length && matchingItemsWithoutExtraClass[0])
        ).name;
    }

    blockFormatIsAvailable(selection) {
        return this.blockFormatIsAvailableMemoized(selection);
    }

    /**
     * Specific behavior for blockquote: insert p at end and remove the last
     * empty node.
     */
    handleSplitBlockquote({ targetNode, targetOffset, blockToSplit }) {
        const closestQuote = closestElement(targetNode, "blockquote");
        const closestBlockNode = closestBlock(targetNode);
        const blockQuotedir = closestQuote && closestQuote.getAttribute("dir");

        if (!closestQuote || closestBlockNode.nodeName !== "BLOCKQUOTE") {
            // If the closestBlockNode is the last element child of its parent
            // and the parent is a blockquote
            // we should move the current block ouside of the blockquote.
            if (
                closestBlockNode.parentElement === closestQuote &&
                closestBlockNode.parentElement.lastElementChild === closestBlockNode &&
                !closestBlockNode.textContent
            ) {
                closestQuote.after(closestBlockNode);

                if (blockQuotedir && !closestBlockNode.getAttribute("dir")) {
                    closestBlockNode.setAttribute("dir", blockQuotedir);
                }
                this.dependencies.selection.setSelection({
                    anchorNode: closestBlockNode,
                    anchorOffset: 0,
                });
                return true;
            }
            return;
        }

        const selection = this.dependencies.selection.getEditableSelection();
        const previousElementSibling = selection.anchorNode?.childNodes[selection.anchorOffset - 1];
        const nextElementSibling = selection.anchorNode?.childNodes[selection.anchorOffset];
        // Double enter at the end of blockquote => we should break out of the blockquote element.
        if (previousElementSibling?.tagName === "BR" && nextElementSibling?.tagName === "BR") {
            nextElementSibling.remove();
            previousElementSibling.remove();
            this.dependencies.split.splitElementBlock({
                targetNode,
                targetOffset,
                blockToSplit,
            });
            this.dependencies.dom.setBlock({
                tagName: this.dependencies.baseContainer.getDefaultNodeName(),
            });
            return true;
        }

        this.dependencies.lineBreak.insertLineBreakElement({ targetNode, targetOffset });
        return true;
    }

    // @todo @phoenix: Move this to a specific Heading plugin?
    /**
     * Specific behavior for headings: do not split in two if cursor at the end but
     * instead create a paragraph.
     * Cursor end of line: <h1>title[]</h1> + ENTER <=> <h1>title</h1><p>[]<br/></p>
     * Cursor in the line: <h1>tit[]le</h1> + ENTER <=> <h1>tit</h1><h1>[]le</h1>
     */
    handleSplitBlockHeading(params) {
        const closestHeading = closestElement(params.targetNode, (element) =>
            headingTags.includes(element.tagName)
        );
        if (closestHeading) {
            const [, newElement] = this.dependencies.split.splitElementBlock(params);
            // @todo @phoenix: if this condition can be anticipated before the split,
            // handle the splitBlock only in such case.
            if (
                newElement &&
                headingTags.includes(newElement.tagName) &&
                !descendants(newElement).some(isVisibleTextNode)
            ) {
                const baseContainer = this.dependencies.baseContainer.createBaseContainer({
                    children: [...newElement.childNodes],
                });
                const dir = newElement.getAttribute("dir");
                if (dir) {
                    baseContainer.setAttribute("dir", dir);
                }
                newElement.replaceWith(baseContainer);
                this.dependencies.selection.setCursorStart(baseContainer);
            }
            return true;
        }
    }

    /**
     * Transform an empty heading or pre at the beginning of the
     * editable into a base container. An empty blockquote is transformed
     * into a base container, regardless of its position in the editable.
     */
    handleDeleteBackward({ startContainer, startOffset, endContainer, endOffset }) {
        // Detect if cursor is at the start of the editable (collapsed range).
        const rangeIsCollapsed = startContainer === endContainer && startOffset === endOffset;
        const closestHandledElement = closestElement(endContainer, handledElemSelector);
        if (!rangeIsCollapsed && closestHandledElement?.tagName !== "BLOCKQUOTE") {
            return;
        }
        // Check if cursor is inside an empty heading, blockquote or pre.
        if (!closestHandledElement || !isEmptyBlock(closestHandledElement)) {
            return;
        }
        // Check if unremovable.
        if (this.dependencies.delete.isUnremovable(closestHandledElement)) {
            return;
        }
        const baseContainer = this.dependencies.baseContainer.createBaseContainer({
            children: [...closestHandledElement.childNodes],
        });
        closestHandledElement.replaceWith(baseContainer);
        this.dependencies.selection.setCursorStart(baseContainer);
        return true;
    }

    updateFontTypeSelectorParams() {
        this.fontType.displayName = this.fontTypeName;
    }

    processContentForClipboard(clonedContents, selection) {
        const commonAncestorElement = closestElement(selection.commonAncestorContainer);
        if (commonAncestorElement && !isBlock(clonedContents.firstChild)) {
            // Get the list of ancestor elements starting from the provided
            // commonAncestorElement up to the block-level element.
            const blockEl = closestBlock(commonAncestorElement);
            const ancestorsList = [
                commonAncestorElement,
                ...ancestors(commonAncestorElement, blockEl),
            ];
            // Wrap rangeContent with clones of their ancestors to keep the styles.
            for (const ancestor of ancestorsList) {
                if (isContentEditableAncestor(ancestor)) {
                    break;
                }
                // Keep the formatting by keeping inline ancestors and paragraph
                // related ones like headings etc.
                if (!isBlock(ancestor) || isParagraphRelatedElement(ancestor)) {
                    const clone = ancestor.cloneNode();
                    clone.append(...childNodes(clonedContents));
                    clonedContents.appendChild(clone);
                }
            }
        }
        return clonedContents;
    }
}
