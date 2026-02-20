import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { removableNodePredicates as deletePluginPredicates } from "@html_editor/core/delete_plugin";
import { isUnremovableQWebElement } from "@html_editor/others/qweb_plugin";
import { isEditable } from "@html_builder/utils/utils";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";

/** @typedef {import("plugins").CSSSelector} CSSSelector */

/**
 * @typedef { Object } RemoveShared
 * @property { RemovePlugin['removeElement'] } removeElement
 */

/**
 * @typedef {((arg: {
 *      removedEl: HTMLElement,
 *      nextTargetEl: HTMLElement,
 *      originPreviousEl: HTMLElement | undefined,
 *      originNextEl: HTMLElement | undefined
 * }) => void)[]} on_removed_handlers
 * @typedef {((toRemoveEl: HTMLElement) => void)[]} on_will_remove_handlers
 *
 * @typedef {((el: HTMLElement) => boolean | undefined)[]} is_node_empty_predicates
 *
 * @typedef {CSSSelector[]} is_unremovable_selector
 */

const removableNodePredicates = [
    (node) => {
        if (!isEditable(node.parentNode)) {
            return false;
        }
    },
    ...deletePluginPredicates,
    (node) => {
        if (isUnremovableQWebElement(node)) {
            return false;
        }
    },
    (node) => {
        if (node.parentNode.matches('[data-oe-type="image"]')) {
            return false;
        }
    },
];

export function isRemovable(el) {
    // TODO: This way of using preidcates is error-prone. Prefer using `checkPredicates`.
    return removableNodePredicates.every((p) => p(el) ?? true);
}

export class RemovePlugin extends Plugin {
    static id = "remove";
    static dependencies = ["builderOptions", "visibility"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        get_overlay_buttons: withSequence(3, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        is_node_empty_predicates: (el) => {
            const systemNodeSelectors = this.getResource("system_node_selectors").join(",");
            if (
                el.textContent.trim() === "" &&
                (!systemNodeSelectors ||
                    [...el.children].every((child) => closestElement(child, systemNodeSelectors)))
            ) {
                return true;
            }
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
            removableNodePredicates.push((node) => {
                if (node.matches(unremovableSelectors.join(", "))) {
                    return false;
                }
            });
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
            class: "oe_snippet_remove text-danger fa fa-trash",
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
            (this.checkPredicates("is_node_empty_predicates", el) ?? false) &&
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
        const originPreviousEl = toRemoveEl.previousElementSibling;
        const originNextEl = toRemoveEl.nextElementSibling;
        const nextTargetEl = this.removeCurrentTarget(toRemoveEl, optionTargetEls);
        this.trigger("on_removed_handlers", {
            removedEl: toRemoveEl,
            nextTargetEl,
            originPreviousEl,
            originNextEl,
        });
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
        this.trigger("on_will_remove_handlers", toRemoveEl);

        // Get the parent and the previous and next visible siblings.
        let parentEl = toRemoveEl.parentElement;
        const previousSiblingEl = this.dependencies.visibility.getVisibleSibling(
            toRemoveEl,
            "prev"
        );
        const nextSiblingEl = this.dependencies.visibility.getVisibleSibling(toRemoveEl, "next");
        if (parentEl.matches(".o_savable:not(body)")) {
            // If we target the savable, we want to reset the selection to the
            // body. If the savable has options, we do not want to show them.
            parentEl = parentEl.closest("body");
        }

        // Remove tooltips.
        selectElements(toRemoveEl, "*").forEach((el) => {
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
