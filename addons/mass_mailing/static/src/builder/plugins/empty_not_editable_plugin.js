import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

export class EmptyNotEditableElementsPlugin extends Plugin {
    static id = "mass_mailing.EmptyNotEditableElements";
    static dependencies = ["selection"];
    resources = {
        normalize_handlers: this.normalize.bind(this),
    };

    /**
     * @param {HTMLElement} element
     */
    normalize(element) {
        const potentiallyEmptyElements = element.querySelectorAll(
            ".o_not_editable [data-oe-zws-empty-inline]"
        );
        potentiallyEmptyElements.forEach((emptyElement) => {
            const emptyNonEditableBlock = closestElement(emptyElement, ".o_not_editable");
            if (isEmptyBlock(emptyNonEditableBlock)) {
                emptyNonEditableBlock.remove();
            }
        });
        if (!this.dependencies.selection.isSelectionInEditable) {
            this.dependencies.selection.resetSelection();
        }
    }
}

registry
    .category("mass_mailing-plugins")
    .add(EmptyNotEditableElementsPlugin.id, EmptyNotEditableElementsPlugin);
