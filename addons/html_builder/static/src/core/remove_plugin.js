import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { unremovableNodePredicates as deletePluginPredicates } from "@html_editor/core/delete_plugin";
import { isUnremovableQWebElement as qwebPluginPredicate } from "@html_editor/others/qweb_plugin";
import { isEditable } from "@html_builder/utils/utils";
import { closestElement } from "@html_editor/utils/dom_traversal";

/** @typedef {import("plugins").CSSSelector} CSSSelector */

/**
 * @typedef { Object } RemoveShared
 * @property { RemovePlugin['removeElement'] } removeElement
 */

/**
 * @typedef {((arg: { removedEl: HTMLElement, nextTargetEl: HTMLElement }) => void)[]} on_removed_handlers
 * @typedef {((toRemoveEl: HTMLElement) => void)[]} on_will_remove_handlers
 *
 * @typedef {((el: HTMLElement) => boolean)[]} empty_node_predicates
 *
 * @typedef {CSSSelector[]} is_unremovable_selector
 */

const unremovableNodePredicates = [
    (node) => !isEditable(node.parentNode),
    ...deletePluginPredicates,
    qwebPluginPredicate,
    (node) => node.parentNode.matches('[data-oe-type="image"]'),
];

export function isRemovable(el) {
    return !unremovableNodePredicates.some((p) => p(el));
}

export class RemovePlugin extends Plugin {
    static id = "remove";
    static dependencies = ["builderOptions", "visibility"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        get_overlay_buttons: withSequence(3, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        empty_node_predicates: (el) => {
            const systemNodeSelectors = this.getResource("system_node_selectors").join(",");
            return (
                el.textContent.trim() === "" &&
                (!systemNodeSelectors ||
                    [...el.children].every((child) => closestElement(child, systemNodeSelectors)))
            );
        },
    };
    static shared = ["removeElement"];

    setup() {
        this.overlayTarget = null;

        const unremovableSelectors = [];
        for (const unremovableSelector of this.getResource("is_unremovable_selector")) {
            unremovableSelectors.push(unremovableSelector);
        }
        if (unremovableSelectors.length) {
            unremovableNodePredicates.push((node) => node.matches(unremovableSelectors.join(", ")));
        }
    }

    getActiveOverlayButtons(target) {
        if (!isRemovable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        const disabledReason = this.dependencies.builderOptions.getRemoveDisabledReason(target);
        buttons.push({
            class: "oe_snippet_remove bg-danger fa fa-trash",
            title: _t("Remove"),
            disabledReason,
            handler: () => {
                this.removeElement(this.overlayTarget);
            },
        });
        return buttons;
    }

    isEmptyAndRemovable(el, optionsTargetEls) {
        return (
            this.getResource("empty_node_predicates").some((predicate) => predicate(el)) &&
            !el.classList.contains("oe_structure") &&
            !el.parentElement.classList.contains("carousel-item") &&
            (!optionsTargetEls.includes(el) ||
                optionsTargetEls.some((targetEl) => targetEl.contains(el))) &&
            isRemovable(el)
        );
    }

    /**
     * Removes the given element and updates the containers if needed.
     *
     * @param {HTMLElement} toRemoveEl the element to remove
     * @param {Boolean} [updateContainers=true] true if the option containers
     *   of the remaining element should be activated.
     */
    removeElement(toRemoveEl, updateContainers = true) {
        // Get the elements having options containers.
        const optionTargetEls = this.getOptionsContainersElements().filter((targetEl) =>
            targetEl.contains(toRemoveEl)
        );
        const nextTargetEl = this.removeCurrentTarget(toRemoveEl, optionTargetEls);
        this.dispatchTo("on_removed_handlers", { removedEl: toRemoveEl, nextTargetEl });
        if (updateContainers) {
            this.dependencies.builderOptions.setNextTarget(nextTargetEl);
        }
    }

    /**
     * Removes the given element from the DOM, as well as its parents when
     * possible, and returns the element of which the options containers should
     * be activated afterwards.
     *
     * @param {HTMLElement} toRemoveEl the element to remove
     * @param {Array<HTMLElement>} optionsTargetEls the current option
     *   containers target elements.
     * @returns {HTMLElement}
     */
    removeCurrentTarget(toRemoveEl, optionsTargetEls) {
        this.dispatchTo("on_will_remove_handlers", toRemoveEl);

        // Get the parent and the previous and next visible siblings.
        let parentEl = toRemoveEl.parentElement;
        const previousSiblingEl = this.dependencies.visibility.getVisibleSibling(
            toRemoveEl,
            "prev"
        );
        const nextSiblingEl = this.dependencies.visibility.getVisibleSibling(toRemoveEl, "next");
        if (parentEl.matches(".o_editable:not(body)")) {
            // If we target the editable, we want to reset the selection to the
            // body. If the editable has options, we do not want to show them.
            parentEl = parentEl.closest("body");
        }

        // Remove tooltips.
        [toRemoveEl, ...toRemoveEl.querySelectorAll("*")].forEach((el) => {
            const tooltip = Tooltip.getInstance(el);
            if (tooltip) {
                tooltip.dispose();
            }
        });

        // Remove the element.
        toRemoveEl.remove();

        // Remove potential last empty text node from the parent.
        if (parentEl) {
            const firstChildEl = parentEl.firstChild;
            if (firstChildEl && !firstChildEl.tagName && firstChildEl.textContent === " ") {
                parentEl.removeChild(firstChildEl);
            }
        }

        // Set the sibling as the next element to activate, if any, otherwise
        // set it as the parent.
        let nextTargetEl = previousSiblingEl || nextSiblingEl;
        if (!nextTargetEl) {
            // Remove potential ancestors (like when removing the last column of
            // a snippet).
            while (!optionsTargetEls.includes(parentEl)) {
                const nextParentEl = parentEl.parentElement;
                if (!nextParentEl) {
                    break;
                }
                if (this.isEmptyAndRemovable(parentEl, optionsTargetEls)) {
                    parentEl.remove();
                }
                parentEl = nextParentEl;
            }

            nextTargetEl = parentEl;
            optionsTargetEls = optionsTargetEls.filter((targetEl) =>
                targetEl.contains(nextTargetEl)
            );
            if (this.isEmptyAndRemovable(parentEl, optionsTargetEls)) {
                nextTargetEl = this.removeCurrentTarget(parentEl, optionsTargetEls);
            }
        }

        return nextTargetEl;
    }

    getOptionsContainersElements() {
        return this.dependencies.builderOptions.getContainers().map((option) => option.element);
    }
}
