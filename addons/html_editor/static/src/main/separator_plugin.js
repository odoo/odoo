import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { closestElement, firstLeaf, lastLeaf, selectElements } from "../utils/dom_traversal";
import { isEmptyBlock, paragraphRelatedElementsSelector } from "../utils/dom_info";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { fillEmpty, removeClass, splitTextNode } from "@html_editor/utils/dom";
import { DIRECTIONS, nodeSize, rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";

export class SeparatorPlugin extends Plugin {
    static id = "separator";
    static dependencies = [
        "baseContainer",
        "delete",
        "dom",
        "history",
        "lineBreak",
        "selection",
        "split",
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
        }),
        content_not_editable_providers: (rootEl) => selectElements(rootEl, "hr"),
        contenteditable_to_remove_selector: "hr[contenteditable]",
        shorthands: [
            {
                literals: ["---"],
                commandId: "insertSeparator",
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.handleSelectionInHr.bind(this),
        deselect_custom_selected_nodes_handlers: this.deselectHR.bind(this),
        clean_handlers: this.deselectHR.bind(this),
        clean_for_save_handlers: ({ root }) => {
            this.deselectHR(root);
        },
    };

    insertSeparator() {
        let selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const block = closestBlock(selection.startContainer);
        this.dispatchTo("before_insert_separator_handlers", block);
        selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const element = closestElement(selection.startContainer, paragraphRelatedElementsSelector);

        if (element && element !== this.editable) {
            const sep = this.document.createElement("hr");
            const firstLeafNode = firstLeaf(block);
            const isSelectionAtEnd =
                lastLeaf(block) === selection.focusNode &&
                selection.focusOffset === nodeSize(selection.focusNode);
            /**
             * Insert the separator before the element when it’s empty
             * or when the caret is at the very start of the block.
             */
            if (
                isEmptyBlock(element) ||
                (selection.anchorNode === firstLeafNode && selection.anchorOffset === 0)
            ) {
                element.before(sep);
            } else if (isSelectionAtEnd) {
                element.after(sep);
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                fillEmpty(baseContainer);
                sep.after(baseContainer);
                this.dependencies.selection.setCursorStart(baseContainer);
            } else {
                const anchorNode = selection.anchorNode;
                const isTextNode = anchorNode.nodeType === Node.TEXT_NODE;
                const newAnchorNode = isTextNode
                    ? splitTextNode(anchorNode, selection.anchorOffset, DIRECTIONS.LEFT) + 1 &&
                      anchorNode
                    : this.dependencies.split
                          .splitElement(anchorNode, selection.anchorOffset)
                          .shift();
                const [newAnchor, newOffset] = rightPos(newAnchorNode);
                this.dependencies.selection.setSelection(
                    { anchorNode: newAnchor, anchorOffset: newOffset },
                    { normalize: false }
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
