import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { splitTextNode, unwrapContents } from "@html_editor/utils/dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { childNodes, closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";

export class InlineCodePlugin extends Plugin {
    static id = "inlineCode";
    static dependencies = ["selection", "history", "input", "split"];
    resources = {
        input_handlers: this.onInput.bind(this),
        beforeinput_handlers: withSequence(1, this.onBeforeInput.bind(this)),
        normalize_handlers: this.normalize.bind(this),
    };

    onBeforeInput() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (!selection.isCollapsed) {
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
                .filter(isTextNode);
            this.insertInlineCode(traversedNodes);
            delete this.historySavePointRestore;
        } else {
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
                this.insertInlineCode([textNode], isClosingForward);
            }
        }
        this.dependencies.history.addStep();
    }

    insertInlineCode(textNode, isClosingForward = true) {
        let codeElement;
        for (let node of textNode) {
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
            codeElement = document.createElement("code");
            codeElement.classList.add("o_inline_code");
            node.before(codeElement);
            codeElement.append(node);
        }
        if (codeElement) {
            if (
                !codeElement.previousSibling ||
                (codeElement.previousSibling.nodeType !== Node.TEXT_NODE &&
                    codeElement.previousSibling.nodeName !== "CODE")
            ) {
                codeElement.before(document.createTextNode("\u200B"));
            }

            isClosingForward && codeElement.after(document.createTextNode("\u200B"));
            // Adjust selection inside or outside the code element
            const selectionTarget = isClosingForward ? codeElement : codeElement.firstChild;
            const anchorOffset = isClosingForward ? nodeSize(codeElement) : 0;

            this.dependencies.selection.setSelection({
                anchorNode: selectionTarget,
                anchorOffset: anchorOffset,
            });
        }
    }
    normalize(root) {
        this.mergeAdjacentInlines(root);
    }

    mergeAdjacentInlines(root) {
        let selectionToRestore = null;
        for (const node of descendants(root)) {
            const previousSibling = node.previousSibling;
            if (
                previousSibling &&
                node.nodeName === "CODE" &&
                previousSibling.nodeName === "CODE"
            ) {
                selectionToRestore ??= this.dependencies.selection.preserveSelection();
                previousSibling.append(...childNodes(node));
                node.remove();
            }
        }
        selectionToRestore?.restore();
    }
}
