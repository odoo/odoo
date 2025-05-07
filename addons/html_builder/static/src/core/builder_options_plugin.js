import { Plugin } from "@html_editor/plugin";
import { uniqueId } from "@web/core/utils/functions";
import { isRemovable } from "./remove_plugin";
import { isClonable } from "./clone_plugin";
import { getElementsWithOption } from "@html_builder/utils/utils";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builder-options";
    static dependencies = [
        "selection",
        "overlay",
        "operation",
        "history",
        "builderOverlay",
        "overlayButtons",
    ];
    static shared = [
        "computeContainers",
        "getContainers",
        "updateContainers",
        "deactivateContainers",
        "getTarget",
        "getPageContainers",
        "getRemoveDisabledReason",
        "getCloneDisabledReason",
        "getReloadSelector",
    ];
    resources = {
        step_added_handlers: () => this.updateContainers(),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        post_undo_handlers: this.restoreContainer.bind(this),
        post_redo_handlers: this.restoreContainer.bind(this),
        // Resources definitions:
        remove_disabled_reason_providers: [
            // ({ el, reasons }) => {
            //     reasons.push(`I hate ${el.dataset.name}`);
            // }
        ],
        clone_disabled_reason_providers: [
            // ({ el, reasons }) => {
            //     reasons.push(`I hate ${el.dataset.name}`);
            // }
        ],
    };

    setup() {
        this.builderOptions = this.getResource("builder_options").map((option) => ({
            ...option,
            id: uniqueId(),
        }));
        this.getResource("patch_builder_options").forEach((option) => {
            this.patchBuilderOptions(option);
        });
        this.builderHeaderMiddleButtons = this.getResource("builder_header_middle_buttons").map(
            (headerMiddleButton) => ({ ...headerMiddleButton, id: uniqueId() })
        );
        this.builderContainerTitle = this.getResource("container_title").map((containerTitle) => ({
            ...containerTitle,
            id: uniqueId(),
        }));
        // doing this manually instead of using addDomListener. This is because
        // addDomListener will ignore all events from protected targets. But in
        // our case, we still want to update the containers.
        this.onClick = this.onClick.bind(this);
        this.editable.addEventListener("click", this.onClick, { capture: true });

        this.lastContainers = [];
        if (this.config.initialTarget) {
            const el = this.editable.querySelector(this.config.initialTarget);
            this.updateContainers(el);
        }
    }

    destroy() {
        this.editable.removeEventListener("click", this.onClick, { capture: true });
    }

    onClick(ev) {
        this.updateContainers(ev.target);
    }

    getReloadSelector(editingElement) {
        for (const container of [...this.lastContainers].reverse()) {
            for (const option of container.options) {
                if (option.reloadTarget) {
                    return option.selector;
                }
            }
        }
        if (editingElement.closest("header")) {
            return "header";
        }
        if (editingElement.closest("main")) {
            return "main";
        }
        if (editingElement.closest("footer")) {
            return "footer";
        }
        return null;
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

        const newContainers = this.computeContainers(this.target);
        // Do not update the containers if they did not change.
        if (newContainers.length === this.lastContainers.length) {
            const previousIds = this.lastContainers.map((c) => c.id);
            const newIds = newContainers.map((c) => c.id);
            const areSameElements = newIds.every((id, i) => id === previousIds[i]);
            if (areSameElements) {
                const previousOptions = this.lastContainers.flatMap((c) => [
                    ...c.options,
                    ...c.headerMiddleButtons,
                    c.containerTitle,
                ]);
                const newOptions = newContainers.flatMap((c) => [
                    ...c.options,
                    ...c.headerMiddleButtons,
                    c.containerTitle,
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

    getTarget() {
        return this.target;
    }

    deactivateContainers() {
        this.target = null;
        this.lastContainers = [];
        this.dispatchTo("change_current_options_containers_listeners", this.lastContainers);
    }

    computeContainers(target) {
        const mapElementsToOptions = (options) => {
            const map = new Map();
            for (const option of options) {
                const { selector, exclude, editableOnly } = option;
                let elements = getClosestElements(target, selector);
                if (!elements.length) {
                    continue;
                }
                elements = elements.filter((el) => checkElement(el, { exclude, editableOnly }));

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
        const elementToContainerTitle = mapElementsToOptions(this.builderContainerTitle);

        // Find the closest element with no options that should still have the
        // overlay buttons.
        let element = target;
        while (element && !elementToOptions.has(element)) {
            if (this.hasOverlayOptions(element)) {
                elementToOptions.set(element, []);
                break;
            }
            element = element.parentElement;
        }

        const previousElementToIdMap = new Map(this.lastContainers.map((c) => [c.element, c.id]));
        return [...elementToOptions]
            .sort(([a], [b]) => (b.contains(a) ? 1 : -1))
            .map(([element, options]) => ({
                id: previousElementToIdMap.get(element) || uniqueId(),
                element,
                options,
                headerMiddleButtons: elementToHeaderMiddleButtons.get(element) || [],
                containerTitle: elementToContainerTitle.get(element)
                    ? elementToContainerTitle.get(element)[0]
                    : {},
                hasOverlayOptions: this.hasOverlayOptions(element),
                isRemovable: isRemovable(element),
                removeDisabledReason: this.getRemoveDisabledReason(element),
                isClonable: isClonable(element),
                cloneDisabledReason: this.getCloneDisabledReason(element),
                optionsContainerTopButtons: this.getOptionsContainerTopButtons(element),
            }));
    }

    getPageContainers() {
        return this.computeContainers(this.editable.querySelector("main"));
    }

    getContainers() {
        return this.lastContainers;
    }

    hasOverlayOptions(el) {
        for (const { hasOption, editableOnly } of this.getResource("has_overlay_options")) {
            if (checkElement(el, { editableOnly }) && hasOption(el)) {
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
        if (revertedStep && revertedStep.extraStepInfos.optionSelection) {
            this.updateContainers(revertedStep.extraStepInfos.optionSelection);
        }
    }
    getRemoveDisabledReason(el) {
        const reasons = [];
        this.dispatchTo("remove_disabled_reason_providers", { el, reasons });
        return reasons.length ? reasons.join(" ") : undefined;
    }
    getCloneDisabledReason(el) {
        const reasons = [];
        this.dispatchTo("clone_disabled_reason_providers", { el, reasons });
        return reasons.length ? reasons.join(" ") : undefined;
    }
    patchBuilderOptions({ target_name, target_element, method, value }) {
        if (!target_name || !target_element || !method || !value) {
            throw new Error(
                `Missing patch_builder_options required parameters: target_name, target_element, method, value`
            );
        }

        const builderOption = this.builderOptions.find((option) => option.name === target_name);
        if (!builderOption) {
            throw new Error(`Builder option ${target_name} not found`);
        }

        switch (method) {
            case "replace":
                builderOption[target_element] = value;
                break;
            case "add":
                if (!builderOption[target_element]) {
                    throw new Error(
                        `Builder option ${target_name} does not have ${target_element}`
                    );
                }
                builderOption[target_element] += `, ${value}`;
                break;
            default:
                throw new Error(`Unknown method ${method}`);
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

/**
 * Checks if the given element is valid in order to have an option.
 *
 * @param {HTMLElement} el
 * @param {Boolean} editableOnly when set to false, the element does not need to
 *     be in an editable area and the checks are therefore lighter.
 *     (= previous data-no-check/noCheck)
 * @param {String} exclude
 * @returns {Boolean}
 */
export function checkElement(el, { editableOnly = true, exclude = "" }) {
    // Unless specified otherwise, the element should be in an editable.
    if (editableOnly && !el.closest(".o_editable")) {
        return false;
    }
    // Check that the element is not to be excluded.
    exclude += `${exclude && ", "}.o_snippet_not_selectable`;
    if (el.matches(exclude)) {
        return false;
    }
    // If an editable is not required, do not check anything else.
    if (!editableOnly) {
        return true;
    }
    // `o_editable_media` bypasses the `o_not_editable` class.
    if (el.matches(".o_editable_media")) {
        return shouldEditableMediaBeEditable(el);
    }
    return !el.matches('.o_not_editable:not(.s_social_media) :not([contenteditable="true"])');
}
