import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { closestBlock } from "../utils/blocks";
import { closestElement } from "../utils/dom_traversal";
import { isListItemElement, paragraphRelatedElementsSelector } from "../utils/dom_info";
import { removeClass } from "@html_editor/utils/dom";
import { withSequence } from "@html_editor/utils/resource";

export class SeparatorPlugin extends Plugin {
    static id = "separator";
    static dependencies = ["selection", "history", "split", "delete", "lineBreak"];
    resources = {
        user_commands: [
            {
                id: "insertSeparator",
                title: _t("Separator"),
                description: _t("Insert a horizontal rule separator"),
                icon: "fa-minus",
                run: this.insertSeparator.bind(this),
            },
        ],
        powerbox_items: withSequence(1, {
            categoryId: "structure",
            commandId: "insertSeparator",
        }),
        /** Handlers */
        normalize_handlers: this.normalize.bind(this),
        selectionchange_handlers: this.handleSelectionInHr.bind(this),
        deselect_custom_selected_nodes_handlers: this.deselectHR.bind(this),
        clean_handlers: this.deselectHR.bind(this),
        clean_for_save_handlers: ({ root }) => {
            for (const el of root.querySelectorAll("hr[contenteditable]")) {
                el.removeAttribute("contenteditable");
            }
            this.deselectHR(root);
        },
    };

    insertSeparator() {
        const selection = this.dependencies.selection.getEditableSelection();
        const sep = this.document.createElement("hr");
        const block = closestBlock(selection.startContainer);
        const element =
            closestElement(selection.startContainer, paragraphRelatedElementsSelector) ||
            (block && !isListItemElement(block) ? block : null);

        if (element && element !== this.editable) {
            element.before(sep);
        }
        this.dependencies.history.addStep();
    }

    normalize(el) {
        if (el.tagName === "HR") {
            el.setAttribute(
                "contenteditable",
                el.hasAttribute("contenteditable") ? el.getAttribute("contenteditable") : "false"
            );
        } else {
            for (const separator of el.querySelectorAll("hr")) {
                separator.setAttribute(
                    "contenteditable",
                    separator.hasAttribute("contenteditable")
                        ? separator.getAttribute("contenteditable")
                        : "false"
                );
            }
        }
    }

    deselectHR(root = this.editable) {
        for (const hr of root.querySelectorAll(".o_selected_hr")) {
            removeClass(hr, "o_selected_hr");
        }
    }

    handleSelectionInHr() {
        this.deselectHR();
        const traversedNodes = this.dependencies.selection.getTraversedNodes({ deep: true });
        for (const node of traversedNodes) {
            if (node.nodeName === "HR") {
                node.classList.toggle("o_selected_hr", true);
            }
        }
    }
}
