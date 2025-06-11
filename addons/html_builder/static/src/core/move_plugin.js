import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import {
    addMobileOrders,
    fillRemovedItemGap,
    removeMobileOrders,
} from "@html_builder/utils/column_layout_utils";
import { isElementInViewport, isMobileView } from "@html_builder/utils/utils";
import { scrollTo } from "@html_builder/utils/scrolling";

export function getVisibleSibling(target, direction) {
    const siblingEls = [...target.parentNode.children];
    const visibleSiblingEls = siblingEls.filter(
        (el) => window.getComputedStyle(el).display !== "none"
    );
    const targetMobileOrder = target.style.order;
    // On mobile, if the target has a mobile order (which is independent
    // from desktop), consider these orders instead of the DOM order.
    if (targetMobileOrder && isMobileView(target)) {
        visibleSiblingEls.sort((a, b) => parseInt(a.style.order) - parseInt(b.style.order));
    }
    const targetIndex = visibleSiblingEls.indexOf(target);
    const siblingIndex = direction === "prev" ? targetIndex - 1 : targetIndex + 1;
    if (siblingIndex === -1 || siblingIndex === visibleSiblingEls.length) {
        return false;
    }
    return visibleSiblingEls[siblingIndex];
}

export class MovePlugin extends Plugin {
    static id = "move";
    resources = {
        has_overlay_options: { hasOption: (el) => this.isMovable(el) },
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        on_cloned_handlers: this.onCloned.bind(this),
        on_remove_handlers: this.onRemove.bind(this),
        on_element_dropped_handlers: this.onElementDropped.bind(this),
        is_movable_selector: [
            {
                selector: "section, .s_showcase .row .row:not(.s_col_no_resize) > div",
                direction: "vertical",
            },
            {
                selector: ".row:not(.s_col_no_resize) > div",
                exclude: ".s_showcase .row .row > div",
                direction: "horizontal",
            },
        ],
    };

    setup() {
        this.overlayTarget = null;
        this.noScroll = false;

        // Compute the selectors.
        const verticalSelector = [];
        const verticalExclude = [];
        const horizontalSelector = [];
        const horizontalExclude = [];
        const noScrollSelector = [];
        for (const movableSelector of this.getResource("is_movable_selector")) {
            const { selector, exclude, direction, noScroll } = movableSelector;
            if (selector) {
                const selectors = direction === "vertical" ? verticalSelector : horizontalSelector;
                selectors.push(selector);
            }
            if (exclude) {
                const excludes = direction === "vertical" ? verticalExclude : horizontalExclude;
                excludes.push(exclude);
            }
            if (noScroll) {
                noScrollSelector.push(selector);
            }
        }

        this.verticalMove = {
            selector: verticalSelector.join(", "),
            exclude: verticalExclude.length > 0 ? verticalExclude.join(", ") : false,
        };
        this.horizontalMove = {
            selector: horizontalSelector.join(", "),
            exclude: horizontalExclude.length > 0 ? horizontalExclude.join(", ") : false,
        };
        this.noScrollSelector = noScrollSelector.length > 0 ? noScrollSelector.join(", ") : false;

        // Needed for compatibility (with already dropped snippets).
        // For each row, check if all its columns are either mobile ordered or
        // not. If they are not consistent, then remove the mobile orders from
        // all of them, to avoid issues.
        const rowEls = this.editable.querySelectorAll(".row");
        for (const rowEl of rowEls) {
            const columnEls = [...rowEl.children];
            const orderedColumnEls = columnEls.filter((el) => el.style.order);
            if (orderedColumnEls.length && orderedColumnEls.length !== columnEls.length) {
                removeMobileOrders(orderedColumnEls);
            }
        }
    }

    isMovable(el) {
        return (
            (el.matches(this.verticalMove.selector) && !el.matches(this.verticalMove.exclude)) ||
            (el.matches(this.horizontalMove.selector) && !el.matches(this.horizontalMove.exclude))
        );
    }

    getActiveOverlayButtons(target) {
        if (!this.isMovable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        this.noScroll = this.overlayTarget.matches(this.noScrollSelector);

        if (!this.areArrowsHidden()) {
            const isVertical =
                this.overlayTarget.matches(this.verticalMove.selector) &&
                !this.overlayTarget.matches(this.verticalMove.exclude);
            const previousSiblingEl = getVisibleSibling(this.overlayTarget, "prev");
            const nextSiblingEl = getVisibleSibling(this.overlayTarget, "next");

            if (previousSiblingEl) {
                const direction = isVertical ? "up" : "left";
                const button = {
                    class: `fa fa-fw fa-angle-${direction}`,
                    title: _t("Move %s", direction),
                    handler: this.onMoveClick.bind(this, "prev"),
                };
                buttons.push(button);
            }

            if (nextSiblingEl) {
                const direction = isVertical ? "down" : "right";
                const button = {
                    class: `fa fa-fw fa-angle-${direction}`,
                    title: _t("Move %s", direction),
                    handler: this.onMoveClick.bind(this, "next"),
                };
                buttons.push(button);
            }
        }
        return buttons;
    }

    onCloned({ cloneEl, originalEl }) {
        if (!this.isMovable(originalEl)) {
            return;
        }
        // If there is a mobile order, the clone must have an order different
        // than the existing ones.
        const hasMobileOrder = !!originalEl.style.order;
        if (hasMobileOrder) {
            const siblingEls = [...originalEl.parentNode.children];
            const maxOrder = Math.max(...siblingEls.map((el) => el.style.order));
            cloneEl.style.order = maxOrder + 1;
        }
    }

    onRemove(toRemoveEl) {
        if (!this.isMovable(toRemoveEl)) {
            return;
        }
        // If there is a mobile order, the gap created by the removed element
        // must be filled in.
        const mobileOrder = toRemoveEl.style.order;
        if (mobileOrder) {
            fillRemovedItemGap(toRemoveEl.parentElement, parseInt(mobileOrder));
        }
    }

    onElementDropped({ droppedEl, dragState }) {
        if (!this.isMovable(droppedEl)) {
            return;
        }
        const parentEl = droppedEl.parentElement;

        // If the dropped element has a mobile order and if it was dropped in
        // another snippet, fill the gap left in the starting snippet.
        const mobileOrder = droppedEl.style.order;
        const { startParentEl } = dragState;
        if (mobileOrder && parentEl !== startParentEl) {
            fillRemovedItemGap(startParentEl, parseInt(mobileOrder));
        }

        // Remove all the mobile orders in the new snippet.
        removeMobileOrders(parentEl.children);
    }

    areArrowsHidden() {
        const isMobile = isMobileView(this.overlayTarget);
        const isGridItem = this.overlayTarget.classList.contains("o_grid_item");
        const siblingsEl = [...this.overlayTarget.parentNode.children];
        const visibleSiblingEl = siblingsEl.find(
            (el) => el !== this.overlayTarget && window.getComputedStyle(el).display !== "none"
        );
        // The arrows are not displayed if:
        // - the target has no visible siblings
        // - the target is a grid item and is not in mobile view
        return !visibleSiblingEl || (isGridItem && !isMobile);
    }

    /**
     * Moves the element in the given direction
     *
     * @param {String} direction "prev" or "next"
     */
    onMoveClick(direction) {
        const isMobile = isMobileView(this.overlayTarget);
        let hasMobileOrder = !!this.overlayTarget.style.order;
        const parentEl = this.overlayTarget.parentNode;
        const siblingEls = parentEl.children;

        // If the target is a column, the ordering in mobile view is independent
        // from the desktop view. If we are in mobile view, we first add the
        // mobile order if there is none yet. In the case where we are not in
        // mobile view, the mobile order is reset.
        const isColumn = parentEl.classList.contains("row");
        if (isMobile && isColumn && !hasMobileOrder) {
            addMobileOrders(siblingEls);
            hasMobileOrder = true;
        } else if (!isMobile && hasMobileOrder) {
            removeMobileOrders(siblingEls);
            hasMobileOrder = false;
        }

        const siblingEl = getVisibleSibling(this.overlayTarget, direction);
        if (hasMobileOrder) {
            // Swap the mobile orders.
            const currentOrder = this.overlayTarget.style.order;
            this.overlayTarget.style.order = siblingEl.style.order;
            siblingEl.style.order = currentOrder;
        } else {
            // Swap the DOM elements.
            siblingEl.insertAdjacentElement(
                direction === "prev" ? "beforebegin" : "afterend",
                this.overlayTarget
            );
        }

        // Scroll to the element.
        if (!this.noScroll && !isElementInViewport(this.overlayTarget)) {
            const { top, height } = this.overlayTarget.getBoundingClientRect();
            const viewportHeight = this.document.defaultView.innerHeight;
            const heightDiff = viewportHeight - height;
            const isBottomHidden = heightDiff < top;
            scrollTo(this.overlayTarget, {
                extraOffset: 50,
                forcedOffset: isBottomHidden ? heightDiff - 50 : undefined,
                duration: 500,
            });
        }
    }
}
