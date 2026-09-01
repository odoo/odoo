/** @odoo-module native */
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { removeClass } from "@html_editor/utils/dom";
import { DIRECTIONS, nodeSize, rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/translation";

import { Plugin } from "../plugin.js";
import { closestBlock } from "../utils/blocks.js";
import { fillEmpty, splitTextNode } from "../utils/dom.js";
import {
    isEmptyBlock,
    isListItemElement,
    paragraphRelatedElementsSelector,
} from "../utils/dom_info.js";
import {
    closestElement,
    firstLeaf,
    lastLeaf,
    selectElements,
} from "../utils/dom_traversal.js";

export class SeparatorPlugin extends Plugin {
    static id = "separator";
    static dependencies = [
        "selection",
        "history",
        "split",
        "delete",
        "dom",
        "lineBreak",
        "baseContainer",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "insertSeparator",
                title: _t("Separator"),
                description: _t("Insert a horizontal rule separator"),
                icon: "fa-minus",
                run: this.insertSeparator.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: withSequence(1, {
            categoryId: "structure",
            commandId: "insertSeparator",
            keywords: [_t("divider"), _t("line")],
        }),
        content_not_editable_providers: (rootEl) => [...selectElements(rootEl, "hr")],
        contenteditable_to_remove_selector: "hr[contenteditable]",
        shorthands: [
            {
                pattern: /^---$/,
                commandId: "insertSeparator",
            },
        ],

        selectionchange_handlers: this.handleSelectionInHr.bind(this),
        deselect_custom_selected_nodes_handlers: this.deselectHR.bind(this),
        clean_for_save_handlers: ({ root }) => {
            this.deselectHR(root);
        },
    };

    insertSeparator() {
        const selection =
            this.dependencies.selection.getSelectionData().deepEditableSelection;
        const block = closestBlock(selection.startContainer);
        const element =
            closestElement(
                selection.startContainer,
                paragraphRelatedElementsSelector,
            ) || (block && !isListItemElement(block) ? block : null);

        if (element && element !== this.editable) {
            const sep = this.document.createElement("hr");
            const firstLeafNode = firstLeaf(block);
            const isSelectionAtEnd =
                lastLeaf(block) === selection.focusNode &&
                selection.focusOffset === nodeSize(selection.focusNode);
            if (
                isEmptyBlock(element) ||
                (selection.anchorNode === firstLeafNode && selection.anchorOffset === 0)
            ) {
                element.before(sep);
            } else if (isSelectionAtEnd) {
                element.after(sep);
                const baseContainer =
                    this.dependencies.baseContainer.createBaseContainer();
                fillEmpty(baseContainer);
                sep.after(baseContainer);
                this.dependencies.selection.setCursorStart(baseContainer);
            } else {
                // Split the block at the cursor and drop the separator in
                // between, so that what follows the cursor stays below it.
                const anchorNode = selection.anchorNode;
                const newAnchorNode =
                    anchorNode.nodeType === Node.TEXT_NODE
                        ? splitTextNode(
                              anchorNode,
                              selection.anchorOffset,
                              DIRECTIONS.LEFT,
                          ) + 1 && anchorNode
                        : this.dependencies.split
                              .splitElement(anchorNode, selection.anchorOffset)
                              .shift();
                const [newAnchor, newOffset] = rightPos(newAnchorNode);
                this.dependencies.selection.setSelection(
                    { anchorNode: newAnchor, anchorOffset: newOffset },
                    { normalize: false },
                );
                this.dependencies.dom.insert(sep);
            }
        }
        this.dependencies.history.addStep();
    }

    deselectHR(root = this.editable) {
        for (const hr of root.querySelectorAll(".o_selected_hr")) {
            removeClass(hr, "o_selected_hr");
        }
    }

    handleSelectionInHr(selectionData) {
        this.deselectHR();
        if (!selectionData.documentSelectionIsInEditable) {
            return;
        }
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        for (const node of targetedNodes) {
            if (node.nodeName === "HR") {
                node.classList.toggle("o_selected_hr", true);
            }
        }
    }
}
