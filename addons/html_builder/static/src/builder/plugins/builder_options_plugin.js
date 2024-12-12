import { Plugin } from "@html_editor/plugin";
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
            this.updateContainers(e.target);
        });

        this.lastContainers = [];
    }

    onSelectionChange(selection) {
        const selectedNodes = this.dependencies.selection.getSelectedNodes();
        let selectionNode;
        if (selectedNodes.length === 0) {
            selectionNode = selection.editableSelection.commonAncestorContainer;
        } else if (selectedNodes.length === 1) {
            selectionNode = selectedNodes[0];
        } else {
            // Some elements are not selectable in the editor but still can be
            // a snippet. The selection will be put in the closest selectable element.
            // Therefore if the selection is collapsed, let the pointerup event handle
            return;
        }
        if (selectionNode.nodeType === Node.TEXT_NODE) {
            selectionNode = selectionNode.parentElement;
        }
        this.updateContainers(selectionNode);
    }

    updateContainers(target) {
        if (target) {
            this.target = target;
        }
        if (!this.target || !this.target.isConnected) {
            this.lastContainers = [];
            this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
            return;
        }
        const elementToOptions = new Map();
        for (const option of this.builderOptions) {
            const { selector, exclude } = option;
            let elements = getClosestElements(this.target, selector);
            if (exclude) {
                elements = elements.filter((el) => !el.matches(exclude));
            }
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
        this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
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
