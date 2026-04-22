import { Plugin } from "@html_editor/plugin";
import { isBlock, closestBlock } from "@html_editor/utils/blocks";
import { unwrapContents } from "@html_editor/utils/dom";
import { isEmptyBlock, isZWS } from "@html_editor/utils/dom_info";
import {
    childNodes,
    closestElement,
    createDOMPathGenerator,
} from "@html_editor/utils/dom_traversal";
import { DIRECTIONS } from "@html_editor/utils/position";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

/** @typedef {((insertedNode: Node) => insertedNode)[]} before_insert_within_pre_processors */

const rightLeafOnlyNotBlockPath = createDOMPathGenerator(DIRECTIONS.RIGHT, {
    leafOnly: true,
    stopTraverseFunction: isBlock,
    stopFunction: isBlock,
});

export class CodeBlockPlugin extends Plugin {
    static id = "codeBlock";
    static dependencies = ["baseContainer", "dom", "selection", "split", "lineBreak", "delete"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        font_type_items: [
            withSequence(50, { name: _t("Code"), tagName: "pre" }),
        ],
        user_commands: [
            {
                id: "setTagPre",
                title: _t("Code"),
                description: _t("Add a code section"),
                icon: "fa-code",
                run: () => this.dependencies.dom.setBlock({ tagName: "pre" }),
                isAvailable: this.blockFormatIsAvailable.bind(this),
            },
        ],
        powerbox_items: [
            withSequence(30, {
                categoryId: "format",
                commandId: "setTagPre",
            }),
        ],
        shorthands: [
            {
                literals: ["```"],
                commandId: "setTagPre",
            },
        ],
        hints: [{ selector: "PRE", text: _t("Code") }],
        split_element_block_overrides: this.handleSplitBlockPRE.bind(this),
        delete_backward_overrides: withSequence(20, this.handleDeleteBackward.bind(this)),
        delete_backward_word_overrides: this.handleDeleteBackward.bind(this),
        before_insert_processors: this.handleInsertWithinPre.bind(this),
    };

    blockFormatIsAvailable(selection) {
        return isHtmlContentSupported(selection) && this.dependencies.dom.canSetBlock();
    }

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
                ? this.dependencies.baseContainer.createBaseContainer({
                      children: [...afterElement.childNodes],
                  })
                : afterElement;
            if (isPreBlock) {
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

    handleDeleteBackward({ startContainer, startOffset, endContainer, endOffset }) {
        const rangeIsCollapsed = startContainer === endContainer && startOffset === endOffset;
        if (!rangeIsCollapsed) {
            return;
        }
        const closestPre = closestElement(endContainer, "PRE");
        if (!closestPre || closestPre.textContent.length) {
            return;
        }
        if (this.dependencies.delete.isUnremovable(closestPre)) {
            return;
        }
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        baseContainer.append(...closestPre.childNodes);
        closestPre.after(baseContainer);
        closestPre.remove();
        this.dependencies.selection.setCursorStart(baseContainer);
        return true;
    }

    handleInsertWithinPre(insertContainer, block) {
        if (block.nodeName !== "PRE") {
            return insertContainer;
        }
        insertContainer = this.processThrough(
            "before_insert_within_pre_processors",
            insertContainer
        );
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
