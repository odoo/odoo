import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { splitTextNode, unwrapContents } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
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
        const traversedBlocks = this.dependencies.selection.getTraversedBlocks();
        const hasTextNode = this.dependencies.selection.getTraversedNodes().some(isTextNode);
        if (!selection.isCollapsed && traversedBlocks.size === 1 && hasTextNode) {
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
            this.dependencies.split.splitSelection();
            const traversedNodes = this.dependencies.selection
                .getSelectedNodes()
                .filter((node) => isTextNode(node) || node.nodeName === "IMG");
            if (traversedNodes.length) {
                const codeElement = this.insertInlineCode(traversedNodes);
                codeElement.after(document.createTextNode("\u200B"));
                this.dependencies.selection.setSelection({
                    anchorNode: codeElement,
                    anchorOffset: nodeSize(codeElement),
                });
                this.dependencies.history.addStep();
            }
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
        this.dependencies.selection.setSelection({
            anchorNode: textNode,
            anchorOffset: offset,
        });
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
            const codeElement = this.insertInlineCode([textNode]);
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
            this.dependencies.history.addStep();
        }
    }

    insertInlineCode(textNode) {
        let codeElement = document.createElement("code");
        codeElement.classList.add("o_inline_code");
        let shouldBreakCodeEl = false;
        // Wrap each selected text node inside a code element
        for (let node of textNode) {
            if (node.nodeName === "IMG" || closestElement(node, "a")) {
                shouldBreakCodeEl = true;
                continue;
            }
            if (shouldBreakCodeEl) {
                codeElement = document.createElement("code");
                codeElement.classList.add("o_inline_code");
                shouldBreakCodeEl = false;
            }
            let parentElement = node.parentElement;
            while (parentElement) {
                // If node is inline code then unwrap it to avoid nested inline code block
                if (node.nodeName === "CODE") {
                    parentElement = node.parentElement;
                    [node] = unwrapContents(node);
                } else if (isBlock(parentElement)) {
                    break;
                } else {
                    // split Element until parent Element
                    node = this.dependencies.split.splitAroundUntil(node, parentElement);
                    parentElement = node.parentElement;
                }
            }
            if (!codeElement.isConnected) {
                node.before(codeElement);
            }
            codeElement.append(node);
        }
        if (
            !codeElement.previousSibling ||
            codeElement.previousSibling.nodeType !== Node.TEXT_NODE
        ) {
            codeElement.before(document.createTextNode("\u200B"));
        }
        return codeElement;
    }
}
