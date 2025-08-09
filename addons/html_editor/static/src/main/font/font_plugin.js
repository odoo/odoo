import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import { leftLeafOnlyNotBlockPath } from "@html_editor/utils/dom_state";
import { isRedundantElement, isVisibleTextNode } from "@html_editor/utils/dom_info";
import {
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
} from "@html_editor/utils/formatting";
import { DIRECTIONS } from "@html_editor/utils/position";
import { _t } from "@web/core/l10n/translation";
import { FontSelector } from "./font_selector";
import { getBaseContainerSelector } from "@html_editor/utils/base_container";
import { withSequence } from "@html_editor/utils/resource";
import { reactive } from "@odoo/owl";
import { FontSizeSelector } from "./font_size_selector";
import { childNodes } from "../../utils/dom_traversal";

export const fontItems = [
    {
        name: _t("Header 1 Display 1"),
        tagName: "h1",
        extraClass: "display-1",
    },
    // TODO @phoenix use them if showExtendedTextStylesOptions is true
    // {
    //     name: _t("Header 1 Display 2"),
    //     tagName: "h1",
    //     extraClass: "display-2",
    // },
    // {
    //     name: _t("Header 1 Display 3"),
    //     tagName: "h1",
    //     extraClass: "display-3",
    // },
    // {
    //     name: _t("Header 1 Display 4"),
    //     tagName: "h1",
    //     extraClass: "display-4",
    // },
    // ----

    { name: _t("Header 1"), tagName: "h1" },
    { name: _t("Header 2"), tagName: "h2" },
    { name: _t("Header 3"), tagName: "h3" },
    { name: _t("Header 4"), tagName: "h4" },
    { name: _t("Header 5"), tagName: "h5" },
    { name: _t("Header 6"), tagName: "h6" },

    {
        name: _t("Normal"),
        tagName: "div",
        // for the FontSelector component
        selector: getBaseContainerSelector("DIV"),
    },
    { name: _t("Paragraph"), tagName: "p" },

    // TODO @phoenix use them if showExtendedTextStylesOptions is true
    // consider baseContainer if enabling them
    // {
    //     name: _t("Light"),
    //     tagName: "p",
    //     extraClass: "lead",
    // },
    // {
    //     name: _t("Small"),
    //     tagName: "p",
    //     extraClass: "small",
    // },
    // ----

    { name: _t("Code"), tagName: "pre" },
    { name: _t("Quote"), tagName: "blockquote" },
];

export const fontSizeItems = [
    {
        variableName: "display-1-font-size",
        className: "display-1-fs",
    },
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
    static dependencies = ["baseContainer", "input", "split", "selection", "dom", "format"];
    resources = {
        user_commands: [
            {
                id: "setTagHeading1",
                title: _t("Heading 1"),
                description: _t("Big section heading"),
                icon: "fa-header",
                run: () => this.dependencies.dom.setTag({ tagName: "H1" }),
            },
            {
                id: "setTagHeading2",
                title: _t("Heading 2"),
                description: _t("Medium section heading"),
                icon: "fa-header",
                run: () => this.dependencies.dom.setTag({ tagName: "H2" }),
            },
            {
                id: "setTagHeading3",
                title: _t("Heading 3"),
                description: _t("Small section heading"),
                icon: "fa-header",
                run: () => this.dependencies.dom.setTag({ tagName: "H3" }),
            },
            {
                id: "setTagParagraph",
                title: _t("Text"),
                description: _t("Paragraph block"),
                icon: "fa-paragraph",
                run: () => {
                    this.dependencies.dom.setTag({
                        tagName: this.dependencies.baseContainer.getDefaultNodeName(),
                    });
                },
            },
            {
                id: "setTagQuote",
                title: _t("Quote"),
                description: _t("Add a blockquote section"),
                icon: "fa-quote-right",
                run: () => this.dependencies.dom.setTag({ tagName: "blockquote" }),
            },
            {
                id: "setTagPre",
                title: _t("Code"),
                description: _t("Add a code section"),
                icon: "fa-code",
                run: () => this.dependencies.dom.setTag({ tagName: "pre" }),
            },
        ],
        toolbar_groups: [
            withSequence(10, {
                id: "font",
            }),
            withSequence(29, {
                id: "font-size",
            }),
        ],
        toolbar_items: [
            {
                id: "font",
                groupId: "font",
                title: _t("Font style"),
                Component: FontSelector,
                props: {
                    getItems: () => fontItems,
                    getDisplay: () => this.font,
                    onSelected: (item) => {
                        this.dependencies.dom.setTag({
                            tagName: item.tagName,
                            extraClass: item.extraClass,
                        });
                        this.updateFontSelectorParams();
                    },
                },
            },
            {
                id: "font-size",
                groupId: "font-size",
                title: _t("Font size"),
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
            },
        ],
        powerbox_categories: withSequence(30, { id: "format", name: _t("Format") }),
        powerbox_items: [
            {
                categoryId: "format",
                commandId: "setTagHeading1",
            },
            {
                categoryId: "format",
                commandId: "setTagHeading2",
            },
            {
                categoryId: "format",
                commandId: "setTagHeading3",
            },
            {
                categoryId: "format",
                commandId: "setTagParagraph",
            },
            {
                categoryId: "structure",
                commandId: "setTagQuote",
            },
            {
                categoryId: "structure",
                commandId: "setTagPre",
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
        input_handlers: this.onInput.bind(this),
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

        before_insert_processors: this.handleInsertWithinPre.bind(this),
    };

    setup() {
        this.fontSize = reactive({ displayName: "" });
        this.font = reactive({ displayName: "" });
    }

    normalize(root) {
        for (const el of selectElements(root, "strong, b, span[style*='font-weight: bolder']")) {
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

        const matchingItems = fontItems.filter((item) => {
            return item.selector ? block.matches(item.selector) : item.tagName === tagName;
        });

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
        return fontSizeItems.flatMap((item) => {
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
        });
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
                (closestBlockNode.textContent || closestBlockNode.nextSibling))
        ) {
            return;
        }

        // Nodes to the right of the split position.
        const nodesAfterTarget = [...rightLeafOnlyNotBlockPath(targetNode, targetOffset)];
        if (
            !nodesAfterTarget.length ||
            (nodesAfterTarget.length === 1 && nodesAfterTarget[0].nodeName === "BR")
        ) {
            // Remove the last empty block node within pre tag
            if (closestBlockNode.nodeName !== "PRE") {
                closestBlockNode.remove();
            }
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            const dir = closestBlockNode.getAttribute("dir") || closestPre.getAttribute("dir");
            if (dir) {
                baseContainer.setAttribute("dir", dir);
            }
            closestPre.after(baseContainer);
            fillEmpty(baseContainer);
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
    handleSplitBlockquote({ targetNode, targetOffset }) {
        const closestQuote = closestElement(targetNode, "blockquote");
        const closestBlockNode = closestBlock(targetNode);
        if (
            !closestQuote ||
            (closestBlockNode.nodeName !== "BLOCKQUOTE" &&
                (closestBlockNode.textContent || closestBlockNode.nextSibling))
        ) {
            return;
        }

        // Nodes to the right of the split position.
        const nodesAfterTarget = [...rightLeafOnlyNotBlockPath(targetNode, targetOffset)];
        if (
            !nodesAfterTarget.length ||
            (nodesAfterTarget.length === 1 && nodesAfterTarget[0].nodeName === "BR")
        ) {
            // Remove the last empty block node within blockquote tag
            if (closestBlockNode.nodeName !== "BLOCKQUOTE") {
                closestBlockNode.remove();
            }
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            const dir = closestBlockNode.getAttribute("dir") || closestQuote.getAttribute("dir");
            if (dir) {
                baseContainer.setAttribute("dir", dir);
            }
            closestQuote.after(baseContainer);
            fillEmpty(baseContainer);
            this.dependencies.selection.setCursorStart(baseContainer);
            return true;
        }
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
                newElement.replaceWith(baseContainer);
                baseContainer.replaceChildren(this.document.createElement("br"));
                this.dependencies.selection.setCursorStart(baseContainer);
            }
            return true;
        }
    }

    /**
     * Transform an empty heading, blockquote or pre at the beginning of the
     * editable into a paragraph.
     */
    handleDeleteBackward({ startContainer, startOffset, endContainer, endOffset }) {
        // Detect if cursor is at the start of the editable (collapsed range).
        const rangeIsCollapsed = startContainer === endContainer && startOffset === endOffset;
        if (!rangeIsCollapsed) {
            return;
        }
        // Check if cursor is inside an empty heading, blockquote or pre.
        const closestHandledElement = closestElement(endContainer, handledElemSelector);
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

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        const blockEl = closestBlock(selection.anchorNode);
        const leftDOMPath = leftLeafOnlyNotBlockPath(selection.anchorNode);
        let spaceOffset = selection.anchorOffset;
        let leftLeaf = leftDOMPath.next().value;
        while (leftLeaf) {
            // Calculate spaceOffset by adding lengths of previous text nodes
            // to correctly find offset position for selection within inline
            // elements. e.g. <p>ab<strong>cd []e</strong></p>
            spaceOffset += leftLeaf.length;
            leftLeaf = leftDOMPath.next().value;
        }
        const precedingText = blockEl.textContent.substring(0, spaceOffset);
        if (/^(#{1,6})\s$/.test(precedingText)) {
            const numberOfHash = precedingText.length - 1;
            const headingToBe = headingTags[numberOfHash - 1];
            this.dependencies.selection.setSelection({
                anchorNode: blockEl.firstChild,
                anchorOffset: 0,
                focusNode: selection.focusNode,
                focusOffset: selection.focusOffset,
            });
            this.dependencies.selection.extractContent(
                this.dependencies.selection.getEditableSelection()
            );
            fillEmpty(blockEl);
            this.dependencies.dom.setTag({ tagName: headingToBe });
        }
    }

    updateFontSelectorParams() {
        this.font.displayName = this.fontName;
    }

    updateFontSizeSelectorParams() {
        this.fontSize.displayName = this.fontSizeName;
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
