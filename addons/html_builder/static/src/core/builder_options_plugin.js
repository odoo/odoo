import { Plugin } from "@html_editor/plugin";
import { uniqueId } from "@web/core/utils/functions";
import { isRemovable } from "./remove_plugin";
import { isClonable } from "./clone_plugin";
import { getElementsWithOption, isElementInViewport } from "@html_builder/utils/utils";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";
import { OptionsContainer } from "@html_builder/sidebar/option_container";

export class BuilderOptionsPlugin extends Plugin {
    static id = "builderOptions";
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
        "findOption",
        "getContainers",
        "updateContainers",
        "deactivateContainers",
        "getTarget",
        "getPageContainers",
        "getRemoveDisabledReason",
        "getCloneDisabledReason",
        "getReloadSelector",
        "setNextTarget",
        "getBuilderOptionContext",
    ];
    resources = {
        before_add_step_handlers: this.onWillAddStep.bind(this),
        step_added_handlers: this.onStepAdded.bind(this),
        post_undo_handlers: (revertedStep) => this.restoreContainers(revertedStep, "undo"),
        post_redo_handlers: (revertedStep) => this.restoreContainers(revertedStep, "redo"),
        clean_for_save_handlers: this.cleanForSave.bind(this),
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
        start_edition_handlers: () => {
            if (this.config.initialTarget) {
                const el = this.editable.querySelector(this.config.initialTarget);
                this.updateContainers(el);
            }
        },
    };

    setup() {
        this.builderOptions = this.getResource("builder_options");
        this.builderOptionsContext = new Map();
        this.builderOptionsDependencies = new Map();
        const options = this.builderOptions.concat([OptionsContainer]);
        for (const Option of options) {
            if (isLegacyOption(Option)) {
                // Support legacy option definition.
                continue;
            }
            this.getBuilderDependencies(Option);
            this.getBuilderOptionContext(Option);
        }

        this.elementsToOptionsTitleComponents = withIds(
            this.getResource("elements_to_options_title_components")
        );
        // todo: remove that resource as we should be able to patch the class the normal way
        this.getResource("patch_builder_options").forEach((option) => {
            this.patchBuilderOptions(option);
        });
        this.builderHeaderMiddleButtons = withIds(
            this.getResource("builder_header_middle_buttons")
        );
        this.builderContainerTitle = withIds(this.getResource("container_title"));
        // doing this manually instead of using addDomListener. This is because
        // addDomListener will ignore all events from protected targets. But in
        // our case, we still want to update the containers.
        this.onClick = this.onClick.bind(this);
        this.editable.addEventListener("click", this.onClick, { capture: true });

        this.lastContainers = [];

        // Selector of elements that should not update/have containers when they
        // are clicked.
        this.notActivableElementsSelector = [
            "#web_editor-top-edit",
            "#oe_manipulators",
            ".oe_drop_zone",
            ".o_notification_manager",
            ".o_we_no_overlay",
            ".ui-autocomplete",
            ".modal .btn-close",
            ".transfo-container",
            ".o_datetime_picker",
        ].join(", ");
    }

    destroy() {
        this.editable.removeEventListener("click", this.onClick, { capture: true });
    }

    onClick(ev) {
        this.dependencies.operation.next(() => {
            this.updateContainers(ev.target);
        });
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

    updateContainers(target, { forceUpdate = false } = {}) {
        if (this.dependencies.history.getIsCurrentStepModified()) {
            console.warn(
                "Should not have any mutations in the current step when you update the container selection"
            );
        }
        if (this.dependencies.history.getIsPreviewing()) {
            return;
        }
        if (target) {
            if (target.closest(this.notActivableElementsSelector)) {
                return;
            }
            this.target = target;
        }
        if (!this.target || !this.target.isConnected) {
            const connectedContainers = this.lastContainers.filter((c) => c.element.isConnected);
            this.target = connectedContainers.at(-1)?.element;
        }

        const newContainers = this.computeContainers(this.target);
        // Do not update the containers if they did not change and are not
        // forced to update.
        if (
            !forceUpdate &&
            this.target?.isConnected &&
            newContainers.length === this.lastContainers.length
        ) {
            const previousIds = this.lastContainers.map((c) => c.id);
            const newIds = newContainers.map((c) => c.id);
            const areSameElements = newIds.every((id, i) => id === previousIds[i]);
            // Check if the overlay options status changed.
            const previousOverlays = this.lastContainers.map((c) => c.hasOverlayOptions);
            const newOverlays = newContainers.map((c) => c.hasOverlayOptions);
            const areSameOverlays = previousOverlays.every((check, i) => check === newOverlays[i]);
            if (areSameElements && areSameOverlays) {
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
        const mapElementsToOptions = (Options) => {
            const map = new Map();
            for (const Option of Options) {
                const { selector, exclude, editableOnly } = Option;
                let elements = getClosestElements(target, selector);
                if (!elements.length) {
                    continue;
                }
                elements = elements.filter((el) => checkElement(el, { exclude, editableOnly }));

                for (const element of elements) {
                    if (map.has(element)) {
                        map.get(element).push(Option);
                    } else {
                        map.set(element, [Option]);
                    }
                }
            }
            return map;
        };
        const elementToOptions = mapElementsToOptions(this.builderOptions);
        const elementToHeaderMiddleButtons = mapElementsToOptions(this.builderHeaderMiddleButtons);
        const elementToContainerTitle = mapElementsToOptions(this.builderContainerTitle);
        const elementToOptionTitleComponents = mapElementsToOptions(
            this.elementsToOptionsTitleComponents
        );

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
        let containers = [...elementToOptions]
            .sort(([a], [b]) => (b.contains(a) ? 1 : -1))
            .map(([element, options]) => ({
                id: previousElementToIdMap.get(element) || uniqueId(),
                element,
                options,
                optionTitleComponents: elementToOptionTitleComponents.get(element) || [],
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
        const lastValidContainerIdx = containers.findLastIndex((c) =>
            this.getResource("no_parent_containers").some((selector) => c.element.matches(selector))
        );
        if (lastValidContainerIdx > 0) {
            containers = containers.slice(lastValidContainerIdx);
        }
        return containers;
    }

    getPageContainers() {
        return this.computeContainers(this.editable.querySelector("main"));
    }

    getContainers() {
        return this.lastContainers;
    }

    hasOverlayOptions(el) {
        // An inner snippet alone in a column should not have overlay options.
        const parentEl = el.parentElement;
        const isAloneInColumn = parentEl?.children.length === 1 && parentEl.matches(".row > div");
        const isInnerSnippet = this.config.snippetModel.isInnerContent(el);
        const keepOptions = this.delegateTo("keep_overlay_options", el);
        if (isInnerSnippet && isAloneInColumn && !keepOptions) {
            return false;
        }

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
        for (const Option of this.builderOptions) {
            const { selector, exclude, cleanForSave } = Option;
            if (!cleanForSave) {
                continue;
            }
            for (const el of getElementsWithOption(root, selector, exclude)) {
                const context = isLegacyOption(Option)
                    ? undefined
                    : this.getBuilderOptionContext(Option);
                cleanForSave(el, context);
            }
        }
    }

    /**
     * Activates the containers of the given element or deactivate them if false
     * is given. They will be (de)activated once the current step is added (see
     * `onStepAdded`).
     *
     * @param {HTMLElement|Boolean} targetEl the element to activate or `false`
     */
    setNextTarget(targetEl) {
        if (this.dependencies.history.getIsPreviewing()) {
            return;
        }
        // Store the next target to activate in the current step.
        this.dependencies.history.setStepExtra("nextTarget", targetEl);
    }

    onWillAddStep() {
        // Store the current target in the current step.
        this.dependencies.history.setStepExtra("currentTarget", this.target);
    }

    onStepAdded({ step }) {
        // If a target is specified, activate its containers, otherwise simply
        // update them.
        const nextTargetEl = step.extraStepInfos.nextTarget;
        if (nextTargetEl) {
            this.updateContainers(nextTargetEl, { forceUpdate: true });
        } else if (nextTargetEl === false) {
            this.deactivateContainers();
        } else {
            this.updateContainers();
        }
    }

    /**
     * Restores the containers of the target stored in the reverted step.
     *
     * @param {Object} revertedStep the step
     * @param {String} mode "undo" or "redo"
     */
    restoreContainers(revertedStep, mode) {
        if (revertedStep && revertedStep.extraStepInfos.currentTarget) {
            let targetEl = revertedStep.extraStepInfos.currentTarget;
            // If the step was supposed to activate another target, activate
            // this one instead.
            const nextTarget = revertedStep.extraStepInfos.nextTarget;
            if (mode === "redo" && (nextTarget || nextTarget === false)) {
                targetEl = nextTarget;
            }
            if (targetEl) {
                this.dispatchTo("on_restore_containers_handlers", targetEl);
                this.updateContainers(targetEl, { forceUpdate: true });
                // Scroll to the target if not visible.
                if (!isElementInViewport(targetEl)) {
                    targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            } else {
                this.deactivateContainers();
            }
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
        if (!target_name || !target_element || !method || (!value && method !== "remove")) {
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
            case "remove":
                delete builderOption[target_element];
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

    /**
     * Finds the given option in the given element closest options container, as
     * well as in the parent containers if specified, and returns it and its
     * target element.
     *
     * @param {HTMLElement} el the element
     * @param {String} optionName the option name
     * @param {Boolean} [allowParent=false] true if the parent containers should
     *   be considered
     * @returns {Object} - `option`: the requested option
     *                   - `targetEl`: the target element of the option
     */
    findOption(el, optionName, allowParent = false) {
        let containers = this.getContainers().filter((container) => container.element.contains(el));
        containers.reverse();
        if (!allowParent) {
            containers = [containers[0]];
        }

        // Find the given option in the active containers and the element on
        // which it applies.
        let targetEl, requestedOption;
        for (const { element, options } of containers) {
            requestedOption = options.find((option) => {
                if (option.OptionComponent) {
                    return option.OptionComponent.name === optionName;
                } else {
                    return option.template.split(".").at(-1) === optionName;
                }
            });
            if (requestedOption) {
                const { applyTo } = requestedOption;
                targetEl = applyTo ? element.querySelector(applyTo) : element;
                break;
            }
        }

        return { option: requestedOption, targetEl };
    }
    /**
     * Get all dependencies of an OptionComponent and all its descendants.
     */
    getBuilderDependencies(OptionComponent) {
        const cachedDeps = this.builderOptionsDependencies.get(OptionComponent);
        if (cachedDeps) {
            return cachedDeps;
        }
        const deps = OptionComponent.dependencies || [];
        this.builderOptionsDependencies.set(OptionComponent, deps);
        const childDeps = Object.values(OptionComponent.components || {}).flatMap(
            this.getBuilderDependencies.bind(this)
        );
        deps.push(...childDeps);
        return deps;
    }
    /**
     * Get all the methods (window, document, getResources, ...) that are available in plugins. Provide the OptionComponent to set the right dependencies.
     */
    getBuilderOptionContext(OptionComponent) {
        const context = this.builderOptionsContext.get(OptionComponent);
        if (!context) {
            const deps = this.getBuilderDependencies(OptionComponent);
            const context = this.__editor.getEditorContext(deps);
            this.builderOptionsContext.set(OptionComponent, context);
            return context;
        }
        return context;
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

function withIds(arr) {
    return arr.map((el) => ({ ...el, id: uniqueId() }));
}

export function isLegacyOption(option) {
    return typeof option === "object";
}
