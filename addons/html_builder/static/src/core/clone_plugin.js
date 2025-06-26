import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { isElementInViewport } from "@html_builder/utils/utils";
import { isRemovable } from "./remove_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

const clonableSelector = "a.btn:not(.oe_unremovable)";

export function isClonable(el) {
    // TODO and isDraggable
    return el.matches(clonableSelector) || isRemovable(el);
}

export class ClonePlugin extends Plugin {
    static id = "clone";
    static dependencies = ["history", "builderOptions"];
    static shared = ["cloneElement"];

    resources = {
        builder_actions: {
            // Maybe rename cloneItem ?
            CloneItemAction,
        },
        get_overlay_buttons: withSequence(2, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        // Resource definitions:
        on_will_clone_handlers: [
            // ({ originalEl: el }) => {
            //     called on the original element before clone
            // }
        ],
        on_cloned_handlers: [
            // ({ cloneEl: cloneEl, originalEl: el }) => {
            //     called after an element was cloned and inserted in the DOM
            // }
        ],
    };

    setup() {
        this.overlayTarget = null;
        this.ignoredClasses = new Set(this.getResource("system_classes"));
        this.ignoredAttrs = new Set(this.getResource("system_attributes"));
    }

    getActiveOverlayButtons(target) {
        if (!isClonable(target)) {
            this.overlayTarget = null;
            return [];
        }
        const buttons = [];
        this.overlayTarget = target;
        const disabledReason = this.dependencies["builderOptions"].getCloneDisabledReason(target);
        buttons.push({
            class: "o_snippet_clone fa fa-clone",
            title: _t("Duplicate"),
            disabledReason,
            handler: () => {
                this.cloneElement(this.overlayTarget, { activateClone: false });
                this.dependencies.history.addStep();
            },
        });
        return buttons;
    }

    /**
     * Duplicates the given element and returns the created clone.
     *
     * @param {HTMLElement} el the element to clone
     * @param {Object}
     *   - `position`: specifies where to position the clone (first parameter of
     *     the `insertAdjacentElement` function)
     *   - `scrollToClone`: true if the we should scroll to the clone (if not in
     *     the viewport), false otherwise
     *   - `activateClone`: true if the option containers of the clone should be
     *     the active ones, false otherwise
     * @returns {HTMLElement}
     */
    cloneElement(el, { position = "afterend", scrollToClone = false, activateClone = true } = {}) {
        this.dispatchTo("on_will_clone_handlers", { originalEl: el });
        const cloneEl = el.cloneNode(true);
        this.cleanElement(cloneEl); // TODO check that
        el.insertAdjacentElement(position, cloneEl);

        // Update the containers if required.
        if (activateClone) {
            this.dependencies["builderOptions"].updateContainers(cloneEl);
        }

        // Scroll to the clone if required and if it is not visible.
        if (scrollToClone && !isElementInViewport(cloneEl)) {
            cloneEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }

        this.dispatchTo("on_cloned_handlers", { cloneEl: cloneEl, originalEl: el });
        return cloneEl;
    }

    cleanElement(toCleanEl) {
        this.ignoredClasses.forEach((ignoredClass) => {
            [toCleanEl, ...toCleanEl.querySelectorAll(`.${ignoredClass}`)].forEach((el) =>
                el.classList.remove(ignoredClass)
            );
        });
        this.ignoredAttrs.forEach((ignoredAttr) => {
            [toCleanEl, ...toCleanEl.querySelectorAll(`[${ignoredAttr}]`)].forEach((el) =>
                el.removeAttribute(ignoredAttr)
            );
        });
    }
}

export class CloneItemAction extends BuilderAction {
    static id = "addItem";
    static dependencies = ["clone", "history"];
    apply({ editingElement, params: { mainParam: itemSelector }, value: position }) {
        const itemEl = editingElement.querySelector(itemSelector);
        this.dependencies.clone.cloneElement(itemEl, { position, scrollToClone: true });
        this.dependencies.history.addStep();
    }
}
