import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { mergeAdjacentTextNodes, splitTextNode } from "@html_editor/utils/dom";
import { closestElement, findFurthest, selectElements } from "@html_editor/utils/dom_traversal";
import { DIRECTIONS } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { DISABLED_NAMESPACE } from "./toolbar/toolbar_plugin";
import { isTextNode, isVisible } from "@html_editor/utils/dom_info";

export class InlineCodePlugin extends Plugin {
    static id = "inlineCode";
    static dependencies = ["clipboard", "feff", "history", "input", "selection", "split"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        input_handlers: this.onInput.bind(this),
        selectionchange_handlers: this.handleSelectionChange.bind(this),
        normalize_handlers: this.normalize.bind(this),

        /** Providers */
        feff_providers: (root, cursors) =>
            [...selectElements(root, ".o_inline_code")].flatMap((code) =>
                this.dependencies.feff.surroundWithFeffs(code, cursors)
            ),
        toolbar_namespace_providers: withSequence(70, (targetedNodes) => {
            const hasInlineCode = targetedNodes.some((node) =>
                closestElement(node, "code.o_inline_code")
            );
            if (
                targetedNodes.length &&
                hasInlineCode &&
                targetedNodes.every(
                    (node) => closestElement(node, "code.o_inline_code") || !isVisible(node)
                )
            ) {
                return DISABLED_NAMESPACE;
            }
        }),

        /** Overrides */
        paste_overrides: (selection, clipboardData) => {
            const caretNode =
                selection.direction === DIRECTIONS.RIGHT
                    ? selection.anchorNode
                    : selection.focusNode;
            if (closestElement(caretNode, "code.o_inline_code")) {
                this.dependencies.clipboard.pasteText(clipboardData.getData("text/plain"));
                return true;
            }
        },

        /** Predicates */
        is_formattable_node_predicates: (node) => {
            if (closestElement(node, "code.o_inline_code")) {
                return false;
            }
        },
        is_powerbox_available_predicates: (node) => {
            if (closestElement(node, "code.o_inline_code")) {
                return false;
            }
        },
        link_compatible_selection_predicates: () => {
            const targetedNodes = this.dependencies.selection.getTargetedNodes();
            if (
                targetedNodes.length &&
                targetedNodes.every((node) => closestElement(node, "code.o_inline_code"))
            ) {
                return false;
            }
        },
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
        const cursor = this.dependencies.selection.preserveSelection();
        mergeAdjacentTextNodes(selection.anchorNode.parentNode, cursor);
        const textNode = cursor.anchor.node;
        const offset = cursor.anchor.offset;
        cursor.restore();
        // We don't apply the code tag if there is no content between the two `
        const textHasTwoTicks = /`[^`]+`/.test(textNode.textContent);
        if (!textHasTwoTicks) {
            this.dependencies.history.addStep();
            return;
        }

        this.dependencies.selection.setSelection({
            anchorNode: textNode,
            anchorOffset: offset,
        });
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
        let codeNextSibling;
        if (isClosingForward) {
            codeNextSibling = this.document.createTextNode("\u200B");
            textNode.after(codeNextSibling);
        }
        const splitLimit = findFurthest(textNode, closestBlock(textNode), (n) => !isBlock(n));
        const splitNode = this.dependencies.split.splitAroundUntil(textNode, splitLimit);
        // Insert code element with plain text.
        const codeElement = this.document.createElement("code");
        codeElement.classList.add("o_inline_code");
        // Remove ticks from the text content.
        codeElement.textContent = splitNode.textContent.substring(
            1,
            splitNode.textContent.length - 1
        );
        splitNode.replaceWith(codeElement);
        if (
            !codeElement.previousSibling ||
            codeElement.previousSibling.nodeType !== Node.TEXT_NODE
        ) {
            codeElement.before(document.createTextNode("\u200B"));
        }
        if (isClosingForward) {
            // Move selection out of code element.
            this.dependencies.selection.setSelection({
                anchorNode: codeNextSibling,
                anchorOffset: 1,
            });
        } else {
            this.dependencies.selection.setSelection({
                anchorNode: codeElement.firstChild,
                anchorOffset: 0,
            });
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
