import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { closestElement, firstLeaf, selectElements } from "../utils/dom_traversal";
import {
    isEmptyBlock,
    isListItemElement,
    paragraphRelatedElementsSelector,
} from "../utils/dom_info";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { removeClass } from "@html_editor/utils/dom";
import { withSequence } from "@html_editor/utils/resource";
import { fillEmpty } from "../utils/dom";

export class SeparatorPlugin extends Plugin {
    static id = "separator";
    static dependencies = ["selection", "history", "split", "delete", "lineBreak", "baseContainer"];
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
        content_not_editable_providers: (rootEl) => [...selectElements(rootEl, "hr")],
        contenteditable_to_remove_selector: "hr[contenteditable]",
        shorthands: [
            {
                pattern: /^---$/,
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
        const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        const block = closestBlock(selection.startContainer);
        const element =
            closestElement(selection.startContainer, paragraphRelatedElementsSelector) ||
            (block && !isListItemElement(block) ? block : null);

        if (element && element !== this.editable) {
            const sep = this.document.createElement("hr");
            const firstLeafNode = firstLeaf(block);
            /**
             * Insert the separator before the element when it’s empty
             * or when the caret is at the very start of the block.
             */
            if (
                isEmptyBlock(element) ||
                (selection.anchorNode === firstLeafNode && selection.anchorOffset === 0)
            ) {
                element.before(sep);
            } else {
                element.after(sep);
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                fillEmpty(baseContainer);
                sep.after(baseContainer);
                this.dependencies.selection.setCursorStart(baseContainer);
            }
        }
        this.dependencies.history.addStep();
    }

    deselectHR(root = this.editable) {
        for (const hr of root.querySelectorAll(".o_selected_hr")) {
            removeClass(hr, "o_selected_hr");
        }
    }

    handleSelectionInHr() {
        this.deselectHR();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        for (const node of targetedNodes) {
            if (node.nodeName === "HR") {
                node.classList.toggle("o_selected_hr", true);
            }
        }
    }
}
