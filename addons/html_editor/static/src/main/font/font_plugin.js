import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { unwrapContents } from "@html_editor/utils/dom";
import {
    isParagraphRelatedElement,
    isRedundantElement,
    isEmptyBlock,
    isVisibleTextNode,
    isZWS,
    isContentEditableAncestor,
} from "@html_editor/utils/dom_info";
import {
    ancestors,
    childNodes,
    closestElement,
    createDOMPathGenerator,
    descendants,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import {
    convertNumericToUnit,
    getCSSVariableValue,
    getHtmlStyle,
    getFontSizeDisplayValue,
    FONT_SIZE_CLASSES,
} from "@html_editor/utils/formatting";
import { DIRECTIONS } from "@html_editor/utils/position";
import { _t } from "@web/core/l10n/translation";
import { FontSelector } from "./font_selector";
import {
    getBaseContainerSelector,
    SUPPORTED_BASE_CONTAINER_NAMES,
} from "@html_editor/utils/base_container";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { FontSizeSelector } from "./font_size_selector";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { weakMemoize } from "@html_editor/utils/functions";

/** @typedef {import("plugins").TranslatedString} TranslatedString */

/**
 * @typedef {((insertedNode: Node) => insertedNode)[]} before_insert_within_pre_processors
 * @typedef {{ name: TranslatedString; tagName: string; extraClass?: string; }[]} font_items
 */

export const fontSizeItems = [
    { variableName: "display-1-font-size", className: "display-1-fs" },
    { variableName: "display-2-font-size", className: "display-2-fs" },
    { variableName: "display-3-font-size", className: "display-3-fs" },
    { variableName: "display-4-font-size", className: "display-4-fs" },
    { variableName: "h1-font-size", className: "h1-fs" },
    { variableName: "h2-font-size", className: "h2-fs" },
    { variableName: "h3-font-size", className: "h3-fs" },
    { variableName: "h4-font-size", className: "h4-fs" },
    { variableName: "h5-font-size", className: "h5-fs" },
    { variableName: "h6-font-size", className: "h6-fs" },
    { variableName: "font-size-base", className: "base-fs" },
    { variableName: "small-font-size", className: "o_small-fs" },
];

const rightLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});

const headingTags = ["H1", "H2", "H3", "H4", "H5", "H6"];
const handledElemSelector = [...headingTags, "PRE", "BLOCKQUOTE"].join(", ");

export class FontPlugin extends Plugin {
    static id = "font";
    static dependencies = [
        "baseContainer",
        "input",
        "split",
        "selection",
        "dom",
        "format",
        "lineBreak",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        font_items: [
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
                // for the FontSelector component
                selector: getBaseContainerSelector("DIV"),
            }),
            withSequence(40, { name: _t("Paragraph"), tagName: "p" }),
            withSequence(50, { name: _t("Code"), tagName: "pre" }),
            withSequence(60, { name: _t("Quote"), tagName: "blockquote" }),
        ],
        user_commands: [
            {
                id: "setTagHeading",
                run: ({ level } = {}) =>
                    this.dependencies.dom.setBlock({ tagName: `H${level ?? 1}` }),
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
            {
                id: "setTagHeading1",
                title: _t("Heading 1"),
                description: _t("Big section heading"),
                icon: "fa-header",
                run: () => this.dependencies.dom.setBlock({ tagName: "H1" }),
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
            {
                id: "setTagHeading2",
                title: _t("Heading 2"),
                description: _t("Medium section heading"),
                icon: "fa-header",
                run: () => this.dependencies.dom.setBlock({ tagName: "H2" }),
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
            {
                id: "setTagHeading3",
                title: _t("Heading 3"),
                description: _t("Small section heading"),
                icon: "fa-header",
                run: () => this.dependencies.dom.setBlock({ tagName: "H3" }),
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
            {
                id: "setTagPre",
                title: _t("Code"),
                description: _t("Add a code section"),
                icon: "fa-code",
                run: () => this.dependencies.dom.setBlock({ tagName: "pre" }),
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
                id: "font",
                groupId: "font",
                namespaces: ["compact", "expanded"],
                description: _t("Select font style"),
                Component: FontSelector,
                props: {
                    getItems: () => this.availableFontItems,
                    getDisplay: () => this.font,
                    onSelected: (item) => {
                        this.dependencies.dom.setBlock({
                            tagName: item.tagName,
                            extraClass: item.extraClass,
                        });
                        this.updateFontSelectorParams();
                    },
                },
                isAvailable: this.blockFormatIsAvailable.bind(this),
            }),
            withSequence(20, {
                id: "font-size",
                groupId: "font",
                namespaces: ["compact", "expanded"],
                description: _t("Select font size"),
                Component: FontSizeSelector,
                props: {
                    getItems: () => this.fontSizeItems,
                    getDisplay: () => this.fontSize,
                    onFontSizeInput: (size) => {
                        this.dependencies.format.formatSelection("fontSize", {
                            formatProps: { size },
                            applyStyle: true,
                        });
                        this.updateFontSizeSelectorParams();
                    },
                    onSelected: (item) => {
                        this.dependencies.format.formatSelection("setFontSizeClassName", {
                            formatProps: { className: item.className },
                            applyStyle: true,
                        });
                        this.updateFontSizeSelectorParams();
                    },
                    onBlur: () => this.dependencies.selection.focusEditable(),
                    document: this.document,
                },
                isAvailable: isHtmlContentSupported,
            }),
        ],
        powerbox_categories: withSequence(5, { id: "format", name: _t("Format") }),
        powerbox_items: [
            {
                categoryId: "format",
                commandId: "setTagHeading1",
                keywords: [_t("title")],
            },
            {
                categoryId: "format",
                commandId: "setTagHeading2",
                keywords: [_t("title")],
            },
            {
                categoryId: "format",
                commandId: "setTagHeading3",
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
            {
                categoryId: "format",
                commandId: "setTagPre",
            },
        ],
        shorthands: [
            {
                pattern: /^#$/,
                commandId: "setTagHeading",
                commandParams: { level: 1 },
            },
            {
                pattern: /^##$/,
                commandId: "setTagHeading",
                commandParams: { level: 2 },
            },
            {
                pattern: /^###$/,
                commandId: "setTagHeading",
                commandParams: { level: 3 },
            },
            {
                pattern: /^####$/,
                commandId: "setTagHeading",
                commandParams: { level: 4 },
            },
            {
                pattern: /^#####$/,
                commandId: "setTagHeading",
                commandParams: { level: 5 },
            },
            {
                pattern: /^######$/,
                commandId: "setTagHeading",
                commandParams: { level: 6 },
            },
            {
                pattern: /^>$/,
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
            { selector: "PRE", text: _t("Code") },
            { selector: "BLOCKQUOTE", text: _t("Quote") },
        ],

        /** Handlers */
        selectionchange_handlers: [
            this.updateFontSelectorParams.bind(this),
            this.updateFontSizeSelectorParams.bind(this),
        ],
        post_undo_handlers: [
            this.updateFontSelectorParams.bind(this),
            this.updateFontSizeSelectorParams.bind(this),
        ],
        post_redo_handlers: [
            this.updateFontSelectorParams.bind(this),
            this.updateFontSizeSelectorParams.bind(this),
        ],
        normalize_handlers: this.normalize.bind(this),

        /** Overrides */
        split_element_block_overrides: [
            this.handleSplitBlockHeading.bind(this),
            this.handleSplitBlockPRE.bind(this),
            this.handleSplitBlockquote.bind(this),
        ],
        delete_backward_overrides: withSequence(20, this.handleDeleteBackward.bind(this)),
        delete_backward_word_overrides: this.handleDeleteBackward.bind(this),

        /** Processors */
        clipboard_content_processors: this.processContentForClipboard.bind(this),
        before_insert_processors: this.handleInsertWithinPre.bind(this),

        format_class_predicates: (className) =>
            [...FONT_SIZE_CLASSES, "o_default_font_size"].includes(className),
    };

    setup() {
        this.fontSize = reactive({ displayName: "" });
        this.font = reactive({ displayName: "" });
        this.blockFormatIsAvailableMemoized = weakMemoize(
            (selection) => isHtmlContentSupported(selection) && this.dependencies.dom.canSetBlock()
        );
        this.availableFontItems = this.getResource("font_items").filter(
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

    get fontName() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        // if (!sel) {
        //     return "Normal";
        // }
        const anchorNode = sel.anchorNode;
        const block = closestBlock(anchorNode);
        const tagName = block.tagName.toLowerCase();

        const matchingItems = this.availableFontItems.filter((item) =>
            item.selector ? block.matches(item.selector) : item.tagName === tagName
        );

        const matchingItemsWitoutExtraClass = matchingItems.filter((item) => !item.extraClass);

        if (!matchingItems.length) {
            return _t("Normal");
        }

        return (
            matchingItems.find((item) => block.classList.contains(item.extraClass)) ||
            (matchingItemsWitoutExtraClass.length && matchingItemsWitoutExtraClass[0])
        ).name;
    }

    get fontSizeName() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        if (!sel) {
            return fontSizeItems[0].name;
        }
        return Math.round(getFontSizeDisplayValue(sel, this.document));
    }

    get fontSizeItems() {
        const style = getHtmlStyle(this.document);
        const nameAlreadyUsed = new Set();
        return fontSizeItems
            .flatMap((item) => {
                const strValue = getCSSVariableValue(item.variableName, style);
                if (!strValue) {
                    return [];
                }
                const remValue = parseFloat(strValue);
                const pxValue = convertNumericToUnit(remValue, "rem", "px", style);
                const roundedValue = Math.round(pxValue);
                if (nameAlreadyUsed.has(roundedValue)) {
                    return [];
                }
                nameAlreadyUsed.add(roundedValue);

                return [{ ...item, tagName: "span", name: roundedValue }];
            })
            .sort((a, b) => a.name - b.name);
    }

    blockFormatIsAvailable(selection) {
        return this.blockFormatIsAvailableMemoized(selection);
    }

    // @todo @phoenix: Move this to a specific Pre/CodeBlock plugin?
    /**
     * Specific behavior for pre: insert newline (\n) in text or insert p at
     * end.
     */
    handleSplitBlockPRE({ targetNode, targetOffset }) {
        const closestPre = closestElement(targetNode, "pre");
        const closestBlockNode = closestBlock(targetNode);
        if (
            !closestPre ||
            (closestBlockNode.nodeName !== "PRE" &&
                ((closestBlockNode.textContent && !isZWS(closestBlockNode)) ||
                    closestBlockNode.nextSibling))
        ) {
            return;
        }

        // Nodes to the right of the split position.
        const nodesAfterTarget = [...rightLeafOnlyNotBlockPath(targetNode, targetOffset)];
        if (
            !nodesAfterTarget.length ||
            (nodesAfterTarget.length === 1 && nodesAfterTarget[0].nodeName === "BR") ||
            isEmptyBlock(closestBlockNode)
        ) {
            // Remove the last empty block node within pre tag
            const [beforeElement, afterElement] = this.dependencies.split.splitElementBlock({
                targetNode,
                targetOffset,
                blockToSplit: closestBlockNode,
            });
            const isPreBlock = beforeElement.nodeName === "PRE";
            const baseContainer = isPreBlock
                ? this.dependencies.baseContainer.createBaseContainer()
                : afterElement;
            if (isPreBlock) {
                baseContainer.replaceChildren(...afterElement.childNodes);
                afterElement.replaceWith(baseContainer);
            } else {
                beforeElement.remove();
                closestPre.after(afterElement);
            }
            const dir = closestBlockNode.getAttribute("dir") || closestPre.getAttribute("dir");
            if (dir) {
                baseContainer.setAttribute("dir", dir);
            }
            this.dependencies.selection.setCursorStart(baseContainer);
        } else {
            const lineBreak = this.document.createElement("br");
            targetNode.insertBefore(lineBreak, targetNode.childNodes[targetOffset]);
            this.dependencies.selection.setCursorEnd(lineBreak);
        }
        return true;
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
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                const dir = newElement.getAttribute("dir");
                if (dir) {
                    baseContainer.setAttribute("dir", dir);
                }
                baseContainer.replaceChildren(...newElement.childNodes);
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
        if (!closestHandledElement || closestHandledElement.textContent.length) {
            return;
        }
        // Check if unremovable.
        if (this.getResource("unremovable_node_predicates").some((p) => p(closestHandledElement))) {
            return;
        }
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        baseContainer.append(...closestHandledElement.childNodes);
        closestHandledElement.after(baseContainer);
        closestHandledElement.remove();
        this.dependencies.selection.setCursorStart(baseContainer);
        return true;
    }

    updateFontSelectorParams() {
        this.font.displayName = this.fontName;
    }

    updateFontSizeSelectorParams() {
        this.fontSize.displayName = this.fontSizeName;
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

    handleInsertWithinPre(insertContainer, block) {
        if (block.nodeName !== "PRE") {
            return insertContainer;
        }
        for (const cb of this.getResource("before_insert_within_pre_processors")) {
            insertContainer = cb(insertContainer);
        }
        const isDeepestBlock = (node) =>
            isBlock(node) && ![...node.querySelectorAll("*")].some(isBlock);
        let linebreak;
        const processNode = (node) => {
            const children = childNodes(node);
            if (isDeepestBlock(node) && node.nextSibling) {
                linebreak = this.document.createTextNode("\n");
                node.append(linebreak);
            }
            if (node.nodeType === Node.ELEMENT_NODE) {
                unwrapContents(node);
            }
            for (const child of children) {
                processNode(child);
            }
        };
        for (const node of childNodes(insertContainer)) {
            processNode(node);
        }
        return insertContainer;
    }
}
