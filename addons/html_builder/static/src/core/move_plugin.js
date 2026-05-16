import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import {
    addMobileOrders,
    fillRemovedItemGap,
    removeMobileOrders,
} from "@html_builder/utils/column_layout_utils";
import { isElementInViewport } from "@html_builder/utils/utils";
import { scrollTo } from "@html_builder/utils/scrolling";
import { localization } from "@web/core/l10n/localization";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {{
 *     selector: CSSSelector;
 *     exclude?: CSSSelector;
 *     direction: "horizontal" | "vertical";
 *     noScroll?: boolean;
 * }[]} is_movable_selector
 */
export class MovePlugin extends Plugin {
    static id = "move";
    static dependencies = ["visibility"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        has_overlay_options: { hasOption: (el) => this.isMovable(el) },
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        on_cloned_handlers: this.onCloned.bind(this),
        on_will_remove_handlers: this.onWillRemove.bind(this),
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
        this.isEditableRTL = this.config.isEditableRTL;
        this.isBackendRTL = localization.direction === "rtl";

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
                removeMobileOrders(orderedColumnEls, this.config.mobileBreakpoint);
            }
        }
    }

    isMovable(el) {
        return (
            (el.matches(this.verticalMove.selector) && !el.matches(this.verticalMove.exclude)) ||
            (el.matches(this.horizontalMove.selector) && !el.matches(this.horizontalMove.exclude))
        );
    }

    /**
     * Returns true if the element is a column visually spanning the full row
     * (including offsets).
     *
     * @param {HTMLElement} el
     * @returns {boolean}
     */
    isFullWidthColumn(el) {
        const rowEl = el.parentElement;
        if (!rowEl || !rowEl.classList.contains("row")) {
            return false;
        }
        const rowRect = rowEl.getBoundingClientRect();
        const columnRect = el.getBoundingClientRect();
        const { marginLeft, marginRight } = getComputedStyle(el);
        const totalWidth = columnRect.width + parseFloat(marginLeft) + parseFloat(marginRight);
        // Allow a small margin to cope with rounding.
        return totalWidth >= rowRect.width - 1;
    }

    getActiveOverlayButtons(target) {
        if (!this.isMovable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        this.noScroll = this.overlayTarget.matches(this.noScrollSelector);
        const reverseButtons = this.isEditableRTL !== this.isBackendRTL;

        if (!this.areArrowsHidden()) {
            const isVertical =
                (this.overlayTarget.matches(this.verticalMove.selector) &&
                    !this.overlayTarget.matches(this.verticalMove.exclude)) ||
                this.isFullWidthColumn(this.overlayTarget);
            const previousSiblingEl = this.dependencies.visibility.getVisibleSibling(
                this.overlayTarget,
                "prev"
            );
            const nextSiblingEl = this.dependencies.visibility.getVisibleSibling(
                this.overlayTarget,
                "next"
            );

            if (previousSiblingEl) {
                const direction = isVertical ? "up" : reverseButtons ? "right" : "left";
                const button = {
                    class: `fa fa-fw fa-angle-${direction}`,
                    title: isVertical
                        ? _t("Move up")
                        : this.isEditableRTL
                        ? _t("Move right")
                        : _t("Move left"),
                    handler: this.onMoveClick.bind(this, "prev"),
                };
                buttons.push(button);
            }

            if (nextSiblingEl) {
                const direction = isVertical ? "down" : reverseButtons ? "left" : "right";
                const button = {
                    class: `fa fa-fw fa-angle-${direction}`,
                    title: isVertical
                        ? _t("Move down")
                        : this.isEditableRTL
                        ? _t("Move left")
                        : _t("Move right"),
                    handler: this.onMoveClick.bind(this, "next"),
                };
                buttons.push(button);
            }

            if (reverseButtons && !isVertical) {
                buttons.reverse();
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

    onWillRemove(toRemoveEl) {
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
        removeMobileOrders(parentEl.children, this.config.mobileBreakpoint);
    }

    areArrowsHidden() {
        const isMobile = this.config.isMobileView(this.overlayTarget);
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
        const isMobile = this.config.isMobileView(this.overlayTarget);
        let hasMobileOrder = !!this.overlayTarget.style.order;
        const parentEl = this.overlayTarget.parentNode;
        const siblingEls = parentEl.children;

        // If the target is a column, the ordering in mobile view is independent
        // from the desktop view. If we are in mobile view, we first add the
        // mobile order if there is none yet. In the case where we are not in
        // mobile view, the mobile order is reset.
        const isColumn = parentEl.classList.contains("row");
        if (isMobile && isColumn && !hasMobileOrder) {
            addMobileOrders(siblingEls, this.config.mobileBreakpoint);
            hasMobileOrder = true;
        } else if (!isMobile && hasMobileOrder) {
            removeMobileOrders(siblingEls, this.config.mobileBreakpoint);
            hasMobileOrder = false;
        }

        const siblingEl = this.dependencies.visibility.getVisibleSibling(
            this.overlayTarget,
            direction
        );
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
