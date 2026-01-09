import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { registry } from "@web/core/registry";

export class EmptyNotEditableElementsPlugin extends Plugin {
    static id = "mass_mailing.EmptyNotEditableElements";
    static dependencies = ["selection"];
    resources = {
        normalize_handlers: [this.normalize.bind(this)],
    };

    /**
     * @param {HTMLElement} element
     */
    normalize(element) {
        const potentiallyEmptyElements = element.querySelectorAll(
            ".o_not_editable :is([data-oe-zws-inline], :not(img, a):empty)"
        );
        potentiallyEmptyElements.forEach((emptyElement) => {
            const emptyBlock = closestBlock(emptyElement);
            if (emptyBlock.closest(".o_not_editable")) {
                emptyBlock.remove();
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
