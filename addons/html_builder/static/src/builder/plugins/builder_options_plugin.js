import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builder-options";
    static dependencies = ["selection", "overlay"];
    resources = {
        selectionchange_handlers: this.onSelectionChange.bind(this),
        step_added_handlers: () => this.updateContainers(),
    };

    setup() {
        // todo: use resources instead of registry
        this.builderOptions = registry
            .category("sidebar-element-option")
            .getEntries()
            .map(([id, option]) => ({ id, ...option }));
        this.builderOptions.sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));
        this.addDomListener(this.editable, "pointerup", (e) => {
            if (!this.dependencies.selection.getEditableSelection().isCollapsed) {
                return;
            }
            this.updateContainers(e.target);
        });

        this.lastContainers = [];
    }

    onSelectionChange(selection) {
        if (selection.editableSelection.isCollapsed) {
            // Some elements are not selectable in the editor but still can be
            // a snippet. The selection will be put in the closest selectable element.
            // Therefore if the selection is collapsed, let the pointerup event handle
            return;
        }
        let selectionNode = selection.editableSelection.commonAncestorContainer;
        if (selectionNode.nodeType === Node.TEXT_NODE) {
            selectionNode = selectionNode.parentElement;
        }
        this.updateContainers(selectionNode);
    }

    updateContainers(target) {
        if (target) {
            this.target = target;
        }
        const elementToOptions = new Map();
        for (const option of this.builderOptions) {
            const { selector } = option;
            const elements = getClosestElements(this.target, selector);
            for (const element of elements) {
                if (elementToOptions.has(element)) {
                    elementToOptions.get(element).push(option);
                } else {
                    elementToOptions.set(element, [option]);
                }
            }
        }

        const previousElementToIdMap = new Map(this.lastContainers.map((c) => [c.element, c.id]));
        this.lastContainers = [...elementToOptions]
            .sort(([a], [b]) => {
                return b.contains(a) ? 1 : -1;
            })
            .map(([element, options]) => ({
                id: previousElementToIdMap.get(element) || uniqueId(),
                element,
                options,
            }));
        for (const handler of this.getResource("change_current_options_containers_listeners")) {
            handler(this.lastContainers);
        }
    }
}

function getClosestElements(element, selector) {
    if (!element) {
        // TODO we should remove it
        return [];
    }
    const parent = element.closest(selector);
    return parent ? [parent, ...getClosestElements(parent.parentElement, selector)] : [];
}
