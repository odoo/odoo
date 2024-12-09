import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builder-options";
    static dependencies = ["selection", "overlay"];
    resources = {
        selectionchange_handlers: this.onSelectionChange.bind(this),
        step_added_handlers: this.updateOptionContainers.bind(this),
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
            this.changeSidebarTarget(e.target);
        });

        this.currentOptionsContainers = reactive([]);
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
        this.changeSidebarTarget(selectionNode);
    }

    getCurrentOptionsByElement() {
        const optionsByElement = new Map();
        for (const option of this.builderOptions) {
            const { selector } = option;
            const elements = getClosestElements(this.currentSelectedElement, selector);
            for (const element of elements) {
                if (optionsByElement.has(element)) {
                    optionsByElement.get(element).push(option);
                } else {
                    optionsByElement.set(element, [option]);
                }
            }
        }
        return optionsByElement;
    }

    changeSidebarTarget(selectedElement) {
        this.currentSelectedElement = selectedElement;
        this.updateOptionContainers();
        for (const handler of this.getResource("change_current_options_containers_listeners")) {
            handler(this.currentOptionsContainers);
        }
        return;
    }

    updateOptionContainers() {
        const optionsByElement = this.getCurrentOptionsByElement();
        const elementsWithContainer = new Set(
            this.currentOptionsContainers.map((optionsContainer) => optionsContainer.element)
        );

        const elementsToRemove = [...elementsWithContainer].filter(
            (el) => !optionsByElement.has(el)
        );
        for (const element of elementsToRemove) {
            const index = this.currentOptionsContainers.findIndex(
                (container) => element === container.element
            );
            this.currentOptionsContainers.splice(index, 1);
        }

        for (const optionContainer of this.currentOptionsContainers) {
            const visibleOptionIds = new Set(
                optionsByElement.get(optionContainer.element).map((option) => option.id)
            );
            for (const option of optionContainer.options) {
                option.isVisible = visibleOptionIds.has(option.id);
            }
        }

        const elementsToAdd = [...optionsByElement.keys()].filter(
            (el) => !elementsWithContainer.has(el)
        );
        for (const element of elementsToAdd) {
            const options = optionsByElement.get(element);
            this.currentOptionsContainers.push({
                id: uniqueId(),
                options: this.getProcessOptions(options),
                element,
            });
        }

        if (elementsToAdd.length) {
            this.currentOptionsContainers.sort((a, b) => (b.element.contains(a.element) ? 1 : -1));
        }
    }

    getProcessOptions(options) {
        const optionsSet = new Set(options);
        return this.builderOptions.map((option) => ({
            ...option,
            isVisible: optionsSet.has(option),
        }));
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
