import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { splitTextNode, unwrapContents } from "@html_editor/utils/dom";
import { isElement, isTextNode, isZwnbsp } from "@html_editor/utils/dom_info";
import { closestElement, selectElements, findFurthest } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";

/** @typedef {((codeElement: HTMLElement) => void)[]} to_inline_code_processors */

export class InlineCodePlugin extends Plugin {
    static id = "inlineCode";
    static dependencies = ["selection", "history", "input", "split", "feff"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        input_handlers: this.onInput.bind(this),
        selectionchange_handlers: this.handleSelectionChange.bind(this),
        normalize_handlers: this.normalize.bind(this),
        feff_providers: (root, cursors) =>
            [...selectElements(root, ".o_inline_code")].flatMap((code) =>
                this.dependencies.feff.surroundWithFeffs(code, cursors)
            ),
    };

    setup() {
        this.addDomListener(this.document, "keydown", this.onKeyDown.bind(this));
    }

    handleSelectionChange() {
        if (this.historySavePointRestore) {
            delete this.historySavePointRestore;
        }
    }

    onKeyDown() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (
            selection.isCollapsed ||
            closestElement(selection.anchorNode, "code") ||
            closestElement(selection.focusNode, "code")
        ) {
            return;
        }
        const targetBlocks = this.dependencies.selection.getTargetedBlocks();
        const hasTextNode = this.dependencies.selection.getTargetedNodes().some(isTextNode);
        if (targetBlocks.size === 1 && hasTextNode) {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
        }
    }

    onInput(ev) {
        const selection = this.dependencies.selection.getEditableSelection();
        if (ev.data !== "`" || closestElement(selection.anchorNode, "code")) {
            return;
        }
        if (this.historySavePointRestore) {
            this.historySavePointRestore();
            let { anchorNode, anchorOffset, focusNode, focusOffset, direction } =
                this.dependencies.split.splitSelection();
            const blockEl = closestBlock(anchorNode);
            // Adjust if anchor/focus directly equals block element
            const deepChild = (node, offset) => (node === blockEl ? node.childNodes[offset] : node);
            anchorNode = deepChild(anchorNode, anchorOffset);
            focusNode = deepChild(focusNode, focusOffset);
            if (direction === DIRECTIONS.LEFT) {
                // Swap anchorNode and focusNode
                [anchorNode, anchorOffset, focusNode, focusOffset] = [
                    focusNode,
                    focusOffset,
                    anchorNode,
                    anchorOffset,
                ];
            }
            const furthestAnchorElement = findFurthest(anchorNode, blockEl, (n) => !isBlock(n));
            let start = this.dependencies.split.splitAroundUntil(anchorNode, furthestAnchorElement);
            const furthestFocusElement = findFurthest(focusNode, blockEl, (n) => !isBlock(n));
            const end = this.dependencies.split.splitAroundUntil(focusNode, furthestFocusElement);

            let codeElement = this.document.createElement("code");
            codeElement.classList.add("o_inline_code");
            start.before(codeElement);
            while (start) {
                if (isElement(start)) {
                    for (const code of selectElements(start, "code")) {
                        start = unwrapContents(code)[0];
                    }
                }
                const next = start.nextSibling;
                if (start.nodeName === "IMG") {
                    // Only create <code> if we still have nodes to process
                    // after this one.
                    if (start !== end && next) {
                        codeElement = this.document.createElement("code");
                        codeElement.classList.add("o_inline_code");
                    }
                } else {
                    if (!codeElement.isConnected) {
                        start.before(codeElement);
                    }
                    codeElement.appendChild(start);
                }
                if (start === end) {
                    break;
                }
                start = next;
            }
            this.dispatchTo("to_inline_code_processors", codeElement);
            this.dependencies.selection.setSelection({
                anchorNode: codeElement,
                anchorOffset: nodeSize(codeElement),
            });
            this.dependencies.history.addStep();
            delete this.historySavePointRestore;
            return;
        }

        // We just inserted a backtick, check if there was another
        // one in the text.
        let textNode = selection.startContainer;
        const wholeText = textNode.wholeText;
        const textHasTwoTicks = /`[^`]+`/.test(wholeText);
        // We don't apply the code tag if there is no content between the two `
        if (textHasTwoTicks && wholeText.replace(/`/g, "").length) {
            let offset = selection.startOffset;
            let sibling = textNode.previousSibling;
            while (sibling && sibling.nodeType === Node.TEXT_NODE) {
                if (!isZwnbsp(sibling)) {
                    offset += sibling.textContent.length;
                }
                sibling.textContent += textNode.textContent;
                textNode.remove();
                textNode = sibling;
                sibling = sibling.previousSibling;
            }
            sibling = textNode.nextSibling;
            while (sibling && sibling.nodeType === Node.TEXT_NODE) {
                if (!isZwnbsp(sibling)) {
                    textNode.textContent += sibling.textContent;
                }
                sibling.remove();
                sibling = sibling.nextSibling;
            }
            this.dependencies.selection.setSelection({
                anchorNode: textNode,
                anchorOffset: offset,
            });
            this.dependencies.history.addStep();
            const insertedBacktickIndex = offset - 1;
            const textBeforeInsertedBacktick = textNode.textContent.substring(
                0,
                insertedBacktickIndex
            );
            let startOffset, endOffset;
            const isClosingForward = textBeforeInsertedBacktick.includes("`");
            if (isClosingForward) {
                // There is a backtick before the new backtick.
                startOffset = textBeforeInsertedBacktick.lastIndexOf("`");
                endOffset = insertedBacktickIndex;
            } else {
                // There is a backtick after the new backtick.
                const textAfterInsertedBacktick = textNode.textContent.substring(offset);
                startOffset = insertedBacktickIndex;
                endOffset = offset + textAfterInsertedBacktick.indexOf("`");
            }
            // Split around the backticks if needed so text starts
            // and ends with a backtick.
            if (endOffset && endOffset < textNode.textContent.length) {
                splitTextNode(textNode, endOffset + 1, DIRECTIONS.LEFT);
            }
            if (startOffset) {
                splitTextNode(textNode, startOffset);
            }
            // Remove ticks.
            textNode.textContent = textNode.textContent.substring(
                1,
                textNode.textContent.length - 1
            );
            // Insert code element.
            const codeElement = this.document.createElement("code");
            codeElement.classList.add("o_inline_code");
            textNode.before(codeElement);
            codeElement.append(textNode);
            if (!codeElement.textContent.length) {
                this.dependencies.history.addStep();
                this.dependencies.selection.setSelection({
                    anchorNode: codeElement.firstChild,
                    anchorOffset: 1,
                });
            } else if (isClosingForward) {
                // Move selection out of code element.
                this.dependencies.history.addStep();
                this.dependencies.selection.setSelection({
                    anchorNode: codeElement.nextSibling,
                    anchorOffset: 1,
                });
            } else {
                this.dependencies.history.addStep();
                this.dependencies.selection.setSelection({
                    anchorNode: codeElement.firstChild,
                    anchorOffset: 0,
                });
            }
        }
    }

    normalize(rootEl) {
        for (const el of selectElements(rootEl, "code.o_inline_code")) {
            if (
                [...el.childNodes].every(
                    (node) => node.nodeType === Node.TEXT_NODE && /^\uFEFF*$/.test(node.nodeValue)
                )
            ) {
                el.remove();
            }
        }
    }
}
