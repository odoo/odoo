import { Plugin } from "@html_editor/plugin";
import { uniqueId } from "@web/core/utils/functions";
import { isRemovable } from "./remove/remove_plugin";
import { isClonable } from "./clone/clone_plugin";
import { getElementsWithOption } from "@html_builder/utils/utils";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builder-options";
    static dependencies = ["selection", "overlay", "operation", "history"];
    static shared = ["getContainers", "updateContainers"];
    resources = {
        step_added_handlers: () => this.updateContainers(),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        post_undo_handlers: this.restoreContainer.bind(this),
        post_redo_handlers: this.restoreContainer.bind(this),
        on_add_element_handlers: ({ elementToAdd }) => this.setTarget(elementToAdd),
    };

    setup() {
        this.builderOptions = this.getResource("builder_options").map((option) => ({
            ...option,
            id: uniqueId(),
        }));
        this.builderHeaderMiddleButtons = this.getResource("builder_header_middle_buttons").map(
            (headerMiddleButton) => ({ ...headerMiddleButton, id: uniqueId() })
        );
        this.addDomListener(this.editable, "pointerup", (e) => {
            this.updateContainers(e.target);
        });

        this.lastContainers = [];
    }

    updateContainers(target) {
        if (this.dependencies.history.getIsCurrentStepModified()) {
            console.warn(
                "Should not have any mutations in the current step when you update the container selection"
            );
        }
        if (this.dependencies.history.getIsPreviewing()) {
            return;
        }
        if (target) {
            this.target = target;
        }
        if (!this.target || !this.target.isConnected) {
            this.lastContainers = this.lastContainers.filter((c) => c.element.isConnected);
            this.target = this.lastContainers.at(-1)?.element;
            this.dependencies.history.setStepExtra("optionSelection", this.target);
            this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
            return;
        }
        if (this.target.dataset.invisible === "1") {
            delete this.target;
            // The element is present on a page but is not visible
            this.lastContainers = [];
            this.dependencies.history.setStepExtra("optionSelection", this.target);
            this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
            return;
        }

        const mapElementsToOptions = (options) => {
            const map = new Map();
            for (const option of options) {
                const { selector, exclude } = option;
                let elements = getClosestElements(this.target, selector);
                if (exclude) {
                    elements = elements.filter((el) => !el.matches(exclude));
                }
                for (const element of elements) {
                    if (map.has(element)) {
                        map.get(element).push(option);
                    } else {
                        map.set(element, [option]);
                    }
                }
            }
            return map;
        };
        const elementToOptions = mapElementsToOptions(this.builderOptions);
        const elementToHeaderMiddleButtons = mapElementsToOptions(this.builderHeaderMiddleButtons);

        // Find the closest element with no options that should still have the
        // overlay buttons.
        let element = this.target;
        while (element && !elementToOptions.has(element)) {
            if (this.hasOverlayOptions(element)) {
                elementToOptions.set(element, []);
                break;
            }
            element = element.parentElement;
        }

        const previousElementToIdMap = new Map(this.lastContainers.map((c) => [c.element, c.id]));
        const newContainers = [...elementToOptions]
            .sort(([a], [b]) => (b.contains(a) ? 1 : -1))
            .map(([element, options]) => ({
                id: previousElementToIdMap.get(element) || uniqueId(),
                element,
                options,
                headerMiddleButtons: elementToHeaderMiddleButtons.get(element) || [],
                hasOverlayOptions: this.hasOverlayOptions(element),
                isRemovable: isRemovable(element),
                isClonable: isClonable(element),
                optionsContainerTopButtons: this.getOptionsContainerTopButtons(element),
            }));

        // Do not update the containers if they did not change.
        if (newContainers.length === this.lastContainers.length) {
            const previousIds = this.lastContainers.map((c) => c.id);
            const newIds = newContainers.map((c) => c.id);
            const areSameElements = newIds.every((id, i) => id === previousIds[i]);
            if (areSameElements) {
                const previousOptions = this.lastContainers.flatMap((c) => [
                    ...c.options,
                    ...c.headerMiddleButtons,
                ]);
                const newOptions = newContainers.flatMap((c) => [
                    ...c.options,
                    ...c.headerMiddleButtons,
                ]);
                const areSameOptions =
                    newOptions.length === previousOptions.length &&
                    newOptions.every((option, i) => option.id === previousOptions[i].id);
                if (areSameOptions) {
                    return;
                }
            }
        }

        this.lastContainers = newContainers;
        this.dependencies.history.setStepExtra("optionSelection", this.target);
        this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
    }

    setTarget(target) {
        this.target = target;
    }

    getContainers() {
        return this.lastContainers;
    }

    hasOverlayOptions(el) {
        for (const hasOverlayOptions of this.getResource("has_overlay_options")) {
            if (hasOverlayOptions(el)) {
                return true;
            }
        }
        return false;
    }

    getOptionsContainerTopButtons(el) {
        const buttons = [];
        for (const getContainerButtons of this.getResource("get_options_container_top_buttons")) {
            buttons.push(...getContainerButtons(el));
            for (const button of buttons) {
                const handler = button.handler;
                button.handler = (...args) => {
                    this.dependencies.operation.next(async () => {
                        await handler(...args);
                        this.dependencies.history.addStep();
                    });
                };
            }
        }
        return buttons;
    }

    cleanForSave({ root }) {
        for (const option of this.builderOptions) {
            const { selector, exclude, cleanForSave } = option;
            if (!cleanForSave) {
                continue;
            }
            for (const el of getElementsWithOption(root, selector, exclude)) {
                cleanForSave(el);
            }
        }
    }

    restoreContainer(revertedStep) {
        if (revertedStep && revertedStep.extra.optionSelection) {
            this.updateContainers(revertedStep.extra.optionSelection);
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
