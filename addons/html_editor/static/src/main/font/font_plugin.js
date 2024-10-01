import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { fillEmpty } from "@html_editor/utils/dom";
import { leftLeafOnlyNotBlockPath } from "@html_editor/utils/dom_state";
import { isVisibleTextNode } from "@html_editor/utils/dom_info";
import {
    closestElement,
    createDOMPathGenerator,
    descendants,
} from "@html_editor/utils/dom_traversal";
import {
    convertNumericToUnit,
    getCSSVariableValue,
    getHtmlStyle,
} from "@html_editor/utils/formatting";
import { DIRECTIONS } from "@html_editor/utils/position";
import { _t } from "@web/core/l10n/translation";
import { FontSelector } from "./font_selector";
import { withSequence } from "@html_editor/utils/resource";

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

    { name: _t("Normal"), tagName: "p" },

    // TODO @phoenix use them if showExtendedTextStylesOptions is true
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
    static name = "font";
    static dependencies = ["split", "selection"];
    resources = {
        split_element_block: [
            this.handleSplitBlockPRE.bind(this),
            this.handleSplitBlockHeading.bind(this),
        ],
        onInput: this.onInput.bind(this),
        handle_delete_backward: withSequence(20, this.handleDeleteBackward.bind(this)),
        handle_delete_backward_word: this.handleDeleteBackward.bind(this),
        toolbarCategory: [
            withSequence(10, {
                id: "font",
            }),
            withSequence(29, {
                id: "font-size",
            }),
        ],
        toolbarItems: [
            {
                id: "font",
                category: "font",
                title: _t("Font style"),
                Component: FontSelector,
                props: {
                    getItems: () => fontItems,
                    command: "SET_TAG",
                },
            },
            {
                id: "font-size",
                category: "font-size",
                title: _t("Font size"),
                Component: FontSelector,
                props: {
                    getItems: () => this.fontSizeItems,
                    isFontSize: true,
                    command: "FORMAT_FONT_SIZE_CLASSNAME",
                    document: this.document,
                },
            },
        ],
        powerboxCategory: withSequence(30, { id: "format", name: _t("Format") }),
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
    };

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
        if (
            this.getResource("isUnremovable").some((predicate) => predicate(closestHandledElement))
        ) {
            return;
        }
        const p = this.document.createElement("p");
        p.append(...closestHandledElement.childNodes);
        closestHandledElement.after(p);
        closestHandledElement.remove();
        this.shared.setCursorStart(p);
        return true;
    }

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.shared.getEditableSelection();
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
            this.shared.setSelection({
                anchorNode: blockEl.firstChild,
                anchorOffset: 0,
                focusNode: selection.focusNode,
                focusOffset: selection.focusOffset,
            });
            this.shared.extractContent(this.shared.getEditableSelection());
            fillEmpty(blockEl);
            this.dispatch("SET_TAG", { tagName: headingToBe });
        }
    }
}
