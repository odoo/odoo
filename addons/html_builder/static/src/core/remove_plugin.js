import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { getVisibleSibling } from "./move_plugin";
import { unremovableNodePredicates as deletePluginPredicates } from "@html_editor/core/delete_plugin";
import { isUnremovableQWebElement as qwebPluginPredicate } from "@html_editor/others/qweb_plugin";
import { isEditable } from "@html_builder/utils/utils";

const unremovableNodePredicates = [
    (node) => !isEditable(node.parentNode),
    ...deletePluginPredicates,
    qwebPluginPredicate,
    (node) => node.parentNode.matches('[data-oe-type="image"]'),
];

export function isRemovable(el) {
    return !unremovableNodePredicates.some((p) => p(el));
}

const layoutElementsSelector = [
    ".o_we_shape",
    ".o_we_bg_filter",
    // Website only
    ".s_parallax_bg",
    ".o_bg_video_container",
].join(",");

export class RemovePlugin extends Plugin {
    static id = "remove";
    static dependencies = ["builderOptions"];
    resources = {
        get_overlay_buttons: withSequence(3, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
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
        const childrenEls = [...el.children];
        // Consider a <figure> element as empty if it only contains a
        // <figcaption> element (e.g. when its image has just been
        // removed).
        const isEmptyFigureEl =
            el.matches("figure") &&
            childrenEls.length === 1 &&
            childrenEls[0].matches("figcaption");

        const isEmpty =
            isEmptyFigureEl ||
            (el.textContent.trim() === "" &&
                childrenEls.every((el) =>
                    // Consider layout-only elements (like bg-shapes) as empty
                    el.matches(layoutElementsSelector)
                ));

        return (
            isEmpty &&
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
        const previousSiblingEl = getVisibleSibling(toRemoveEl, "prev");
        const nextSiblingEl = getVisibleSibling(toRemoveEl, "next");
        if (parentEl.matches(".o_savable:not(body)")) {
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
