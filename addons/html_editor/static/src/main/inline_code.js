import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { splitTextNode, unwrapContents } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { closestElement, findFurthest, selectElements } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";

export class InlineCodePlugin extends Plugin {
    static id = "inlineCode";
    static dependencies = ["selection", "history", "input", "split"];
    resources = {
        input_handlers: this.onInput.bind(this),
        beforeinput_handlers: withSequence(1, this.onBeforeInput.bind(this)),
    };

    onBeforeInput() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (
            selection.isCollapsed ||
            closestElement(selection.anchorNode, "a") ||
            closestElement(selection.focusNode, "a")
        ) {
            return;
        }
        const traversedBlocks = this.dependencies.selection.getTraversedBlocks();
        const hasTextNode = this.dependencies.selection.getTraversedNodes().some(isTextNode);
        if (traversedBlocks.size === 1 && hasTextNode) {
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
            if (direction === false) {
                // Swap anchorNode and focusNode
                [anchorNode, anchorOffset, focusNode, focusOffset] = [
                    focusNode,
                    focusOffset,
                    anchorNode,
                    anchorOffset,
                ];
            }

            const furthestAnchorElement = findFurthest(
                anchorNode,
                closestBlock(anchorNode),
                (n) => !isBlock(n)
            );
            let start = this.dependencies.split.splitAroundUntil(anchorNode, furthestAnchorElement);
            const furthestFocusElement = findFurthest(
                focusNode,
                closestBlock(focusNode),
                (n) => !isBlock(n)
            );
            const end = this.dependencies.split.splitAroundUntil(focusNode, furthestFocusElement);

            // After splitting the anchorNode, if the start element contains
            // the focusNode, splitting the focusNode could cause the start
            // element to be detached from the DOM. In this case, find the
            // valid start element again to ensure it remains connected.
            if (!start.isConnected) {
                start = findFurthest(anchorNode, closestBlock(anchorNode), (n) => !isBlock(n));
            }
            const codeElement = this.document.createElement("code");
            codeElement.classList.add("o_inline_code");
            start.before(codeElement);
            while (start) {
                const next = start.nextSibling;
                codeElement.appendChild(start);
                if (start.nodeType === Node.ELEMENT_NODE) {
                    for (const code of selectElements(start, "code")) {
                        unwrapContents(code);
                    }
                }
                if (start === end) {
                    break;
                }
                start = next;
            }
            if (
                !codeElement.previousSibling ||
                codeElement.previousSibling.nodeType !== Node.TEXT_NODE
            ) {
                codeElement.before(document.createTextNode("\u200B"));
            }
            codeElement.after(document.createTextNode("\u200B"));
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
        let offset = selection.startOffset;
        let sibling = textNode.previousSibling;
        while (sibling && sibling.nodeType === Node.TEXT_NODE) {
            offset += sibling.textContent.length;
            sibling.textContent += textNode.textContent;
            textNode.remove();
            textNode = sibling;
            sibling = textNode.previousSibling;
        }
        sibling = textNode.nextSibling;
        while (sibling && sibling.nodeType === Node.TEXT_NODE) {
            textNode.textContent += sibling.textContent;
            sibling.remove();
            sibling = textNode.nextSibling;
        }
        this.dependencies.selection.setSelection({ anchorNode: textNode, anchorOffset: offset });
        const textHasTwoTicks = /`.*`/.test(textNode.textContent);
        // We don't apply the code tag if there is no content between the two `
        if (textHasTwoTicks && textNode.textContent.replace(/`/g, "").length) {
            this.dependencies.history.addStep();
            const insertedBacktickIndex = offset - 1;
            const textBeforeInsertedBacktick = textNode.textContent.substring(
                0,
                insertedBacktickIndex - 1
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
            if (
                !codeElement.previousSibling ||
                codeElement.previousSibling.nodeType !== Node.TEXT_NODE
            ) {
                codeElement.before(document.createTextNode("\u200B"));
            }
            if (isClosingForward) {
                // Move selection out of code element.
                codeElement.after(document.createTextNode("\u200B"));
                this.dependencies.selection.setSelection({
                    anchorNode: codeElement.nextSibling,
                    anchorOffset: 1,
                });
            } else {
                this.dependencies.selection.setSelection({
                    anchorNode: codeElement.firstChild,
                    anchorOffset: 0,
                });
            }
        }
        this.dependencies.history.addStep();
    }
}
