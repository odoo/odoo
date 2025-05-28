import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { resizeGrid } from "@html_builder/utils/grid_layout_utils";
import { getVisibleSibling } from "./move_plugin";
import { unremovableNodePredicates as deletePluginPredicates } from "@html_editor/core/delete_plugin";
import { isUnremovableQWebElement as qwebPluginPredicate } from "@html_editor/others/qweb_plugin";
import { isEditable } from "@html_builder/utils/utils";

// TODO (see forceNoDeleteButton) make a resource in the options plugins to not
// duplicate some selectors.
const unremovableSelectors = [
    ".s_carousel .carousel-item",
    ".s_quotes_carousel .carousel-item",
    ".s_carousel_intro .carousel-item",
    ".o_mega_menu",
    ".o_mega_menu > section",
    ".s_dynamic_snippet_title",
    ".s_table_of_content_navbar_wrap",
    ".s_table_of_content_main",
    ".nav-item",
].join(", ");

const unremovableNodePredicates = [
    (node) => !isEditable(node.parentNode),
    ...deletePluginPredicates,
    qwebPluginPredicate,
    (node) => node.parentNode.matches('[data-oe-type="image"]'),
    (node) => node.matches(unremovableSelectors),
];

export function isRemovable(el) {
    return !unremovableNodePredicates.some((p) => p(el));
}

const layoutElementsSelector = [
    ".o_we_shape",
    ".o_we_bg_filter",
    ".s_parallax_bg",
    ".o_bg_video_container",
].join(",");

export class RemovePlugin extends Plugin {
    static id = "remove";
    static dependencies = ["history", "builderOptions"];
    resources = {
        get_overlay_buttons: withSequence(3, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
    };
    static shared = ["removeElement", "removeElementAndUpdateContainers"];

    setup() {
        this.overlayTarget = null;
    }

    getActiveOverlayButtons(target) {
        if (!isRemovable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        const disabledReason = this.dependencies["builderOptions"].getRemoveDisabledReason(target);
        buttons.push({
            class: "oe_snippet_remove bg-danger fa fa-trash",
            title: _t("Remove"),
            disabledReason,
            handler: () => {
                this.removeElementAndUpdateContainers(this.overlayTarget);
            },
        });
        return buttons;
    }

    isEmptyAndRemovable(el) {
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

        const optionsTargetEls = this.dependencies["builderOptions"]
            .computeContainers(el)
            .map((e) => e.element);

        return (
            isEmpty &&
            !el.classList.contains("oe_structure") &&
            !el.parentElement.classList.contains("carousel-item") &&
            // TODO check if ok (parent editable)
            (!optionsTargetEls.includes(el) ||
                optionsTargetEls.some((targetEl) => targetEl.contains(el))) &&
            isRemovable(el)
        );
    }

    removeElementAndUpdateContainers(el) {
        const elementToSelect = this.removeElement(el);
        this.dependencies.history.addStep();
        this.dependencies["builderOptions"].updateContainers(elementToSelect);
    }

    removeElement(el) {
        const elementToSelect = this.removeCurrentTarget(el);
        this.dispatchTo("after_remove_handlers", el);
        return elementToSelect;
    }

    removeCurrentTarget(toRemoveEl) {
        // Get the elements having options containers.
        let optionsTargetEls = this.getOptionsContainersElements();

        // TODO invisible element
        // TODO will_remove_snippet
        this.dispatchTo("on_remove_handlers", toRemoveEl);

        let parentEl = toRemoveEl.parentElement;
        const previousSiblingEl = getVisibleSibling(toRemoveEl, "prev");
        const nextSiblingEl = getVisibleSibling(toRemoveEl, "next");
        if (parentEl.matches(".o_editable:not(body)")) {
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

        // Resize the grid, if any, to have the correct row count.
        // Must be done here and not in a dedicated onRemove method because
        // onRemove is called before actually removing the element and it
        // should be the case in order to resize the grid.
        if (toRemoveEl.classList.contains("o_grid_item")) {
            resizeGrid(parentEl);
        }

        if (parentEl) {
            const firstChildEl = parentEl.firstChild;
            if (firstChildEl && !firstChildEl.tagName && firstChildEl.textContent === " ") {
                parentEl.removeChild(firstChildEl);
            }
        }

        let nextElementToSelect;
        if (previousSiblingEl || nextSiblingEl) {
            // Activate the previous or next visible siblings if any.
            nextElementToSelect = previousSiblingEl || nextSiblingEl;
        } else {
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
            nextElementToSelect = parentEl;

            optionsTargetEls = this.getOptionsContainersElements();
            if (this.isEmptyAndRemovable(parentEl, optionsTargetEls)) {
                nextElementToSelect = this.removeCurrentTarget(parentEl);
            }
        }

        // TODO is it still necessary ?
        this.editable
            .querySelectorAll(".note-control-selection")
            .forEach((el) => (el.style.display = "none"));
        this.editable.querySelectorAll(".o_table_handler").forEach((el) => el.remove());

        return nextElementToSelect;
        // TODO:
        // - trigger snippet_removed
        //   - display message in the editor if no snippets,
        //   - update invisible (already OK (see onChange))
        //   - update undroppable snippets
        // - cover update for translation mode
    }

    getOptionsContainersElements() {
        return this.dependencies["builderOptions"].getContainers().map((option) => option.element);
    }
}
