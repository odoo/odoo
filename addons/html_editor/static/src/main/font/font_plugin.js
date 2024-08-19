import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { fillEmpty } from "@html_editor/utils/dom";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import {
    closestElement,
    createDOMPathGenerator,
    descendants,
} from "@html_editor/utils/dom_traversal";
import {
    convertNumericToUnit,
    getCSSVariableValue,
    getFontSizeDisplayValue,
    getHtmlStyle,
} from "@html_editor/utils/formatting";
import { DIRECTIONS } from "@html_editor/utils/position";
import { _t } from "@web/core/l10n/translation";
import { ToolbarItemSelector } from "./toolbar_item_selector";

const tagItems = [
    {
        name: _t("Header 1 Display 1"),
        tagName: "h1",
        extraClass: "display-1",
    },
    // TODO @phoenix use them if showExtendedTextStylesOptions is true
    {
        name: _t("Header 1 Display 2"),
        tagName: "h1",
        extraClass: "display-2",
    },
    {
        name: _t("Header 1 Display 3"),
        tagName: "h1",
        extraClass: "display-3",
    },
    {
        name: _t("Header 1 Display 4"),
        tagName: "h1",
        extraClass: "display-4",
    },
    // ----

    { name: _t("Header 1"), tagName: "h1" },
    { name: _t("Header 2"), tagName: "h2" },
    { name: _t("Header 3"), tagName: "h3" },
    { name: _t("Header 4"), tagName: "h4" },
    { name: _t("Header 5"), tagName: "h5" },
    { name: _t("Header 6"), tagName: "h6" },

    { name: _t("Normal"), tagName: "p" },

    // TODO @phoenix use them if showExtendedTextStylesOptions is true
    {
        name: _t("Light"),
        tagName: "p",
        extraClass: "lead",
    },
    {
        name: _t("Small"),
        tagName: "p",
        extraClass: "small",
    },
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
    static name = "font";
    static dependencies = ["split", "selection"];
    /** @type { (p: FontPlugin) => Record<string, any> } */
    static resources = (p) => ({
        split_element_block: [
            { callback: p.handleSplitBlockPRE.bind(p) },
            { callback: p.handleSplitBlockHeading.bind(p) },
        ],
        handle_delete_backward: { callback: p.handleDeleteBackward.bind(p), sequence: 20 },
        handle_delete_backward_word: { callback: p.handleDeleteBackward.bind(p), sequence: 20 },
        toolbarCategory: [
            {
                id: "typo",
                sequence: 10,
            },
            { id: "size", sequence: 29 },
        ],
        toolbarItems: [
            {
                id: "typo",
                category: "typo",
                Component: ToolbarItemSelector,
                props: {
                    getItems: () => tagItems,
                    getEditableSelection: p.shared.getEditableSelection.bind(p),
                    onSelected: (item) => p.dispatch("SET_TAG", item),
                    getItemFromSelection: (selection) => {
                        const anchorNode = selection.anchorNode;
                        const block = closestBlock(anchorNode);
                        const tagName = block.tagName.toLowerCase();

                        const matchingItems = tagItems.filter((item) => {
                            return item.tagName === tagName;
                        });

                        if (!matchingItems.length) {
                            return { name: "Normal" };
                        }

                        return (
                            matchingItems.find((item) =>
                                block.classList.contains(item.extraClass)
                            ) || matchingItems[0]
                        );
                    },
                },
            },
            {
                id: "font-size",
                category: "size",
                Component: ToolbarItemSelector,
                props: {
                    getItems: () => p.fontSizeItems,
                    getEditableSelection: p.shared.getEditableSelection.bind(p),
                    onSelected: (item) => p.dispatch("FORMAT_FONT_SIZE_CLASSNAME", item),
                    getItemFromSelection: (selection) => {
                        return {
                            name: Math.round(getFontSizeDisplayValue(selection, p.document)),
                        };
                    },
                },
            },
        ],
        powerboxCategory: { id: "format", name: _t("Format"), sequence: 30 },
        powerboxItems: [
            {
                name: _t("Heading 1"),
                description: _t("Big section heading"),
                category: "format",
                fontawesome: "fa-header",
                action(dispatch) {
                    dispatch("SET_TAG", { tagName: "H1" });
                },
            },
            {
                name: _t("Heading 2"),
                description: _t("Medium section heading"),
                category: "format",
                fontawesome: "fa-header",
                action(dispatch) {
                    dispatch("SET_TAG", { tagName: "H2" });
                },
            },
            {
                name: _t("Heading 3"),
                description: _t("Small section heading"),
                category: "format",
                fontawesome: "fa-header",
                action(dispatch) {
                    dispatch("SET_TAG", { tagName: "H3" });
                },
            },
            {
                category: "format",
                name: _t("Text"),
                description: _t("Paragraph block"),
                fontawesome: "fa-paragraph",
                action(dispatch) {
                    dispatch("SET_TAG", { tagName: "P" });
                },
            },
            {
                category: "structure",
                name: _t("Quote"),
                description: _t("Add a blockquote section"),
                fontawesome: "fa-quote-right",
                action(dispatch) {
                    dispatch("SET_TAG", { tagName: "blockquote" });
                },
            },
            {
                category: "structure",
                name: _t("Code"),
                description: _t("Add a code section"),
                fontawesome: "fa-code",
                action(dispatch) {
                    dispatch("SET_TAG", { tagName: "pre" });
                },
            },
        ],
        emptyBlockHints: [
            { selector: "H1", hint: _t("Heading 1") },
            { selector: "H2", hint: _t("Heading 2") },
            { selector: "H3", hint: _t("Heading 3") },
            { selector: "H4", hint: _t("Heading 4") },
            { selector: "H5", hint: _t("Heading 5") },
            { selector: "H6", hint: _t("Heading 6") },
            { selector: "PRE", hint: _t("Code") },
            { selector: "BLOCKQUOTE", hint: _t("Quote") },
        ],
    });

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
        if (!closestPre) {
            return;
        }

        // Nodes to the right of the split position.
        const nodesAfterTarget = [...rightLeafOnlyNotBlockPath(targetNode, targetOffset)];
        if (
            !nodesAfterTarget.length ||
            (nodesAfterTarget.length === 1 && nodesAfterTarget[0].nodeName === "BR")
        ) {
            const p = this.document.createElement("p");
            closestPre.after(p);
            fillEmpty(p);
            this.shared.setCursorStart(p);
        } else {
            const lineBreak = this.document.createElement("br");
            targetNode.insertBefore(lineBreak, targetNode.childNodes[targetOffset]);
            this.shared.setCursorEnd(lineBreak);
        }
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
            const [, newElement] = this.shared.splitElementBlock(params);
            // @todo @phoenix: if this condition can be anticipated before the split,
            // handle the splitBlock only in such case.
            if (
                headingTags.includes(newElement.tagName) &&
                !descendants(newElement).some(isVisibleTextNode)
            ) {
                const p = this.document.createElement("P");
                newElement.replaceWith(p);
                p.replaceChildren(this.document.createElement("br"));
                this.shared.setCursorStart(p);
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
        if (this.resources.isUnremovable.some((predicate) => predicate(closestHandledElement))) {
            return;
        }
        const p = this.document.createElement("p");
        p.append(...closestHandledElement.childNodes);
        closestHandledElement.after(p);
        closestHandledElement.remove();
        this.shared.setCursorStart(p);
        return true;
    }
}
