import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import {
    addMobileOrders,
    fillRemovedItemGap,
    removeMobileOrders,
} from "@html_builder/utils/column_layout_utils";
import { isMobileView } from "@html_builder/utils/utils";

const moveUpOrDown = {
    selector: [
        "section",
        ".s_accordion .accordion-item",
        ".s_showcase .row .row:not(.s_col_no_resize) > div",
        ".s_hr",
        // In snippets files
        ".s_pricelist_boxed_item",
        ".s_pricelist_cafe_item",
        ".s_product_catalog_dish",
        ".s_timeline_list_row",
        ".s_timeline_row",
        "s_timeline_images_row",
    ].join(", "),
};

const moveLeftOrRight = {
    selector: [
        ".row:not(.s_col_no_resize) > div",
        ".nav-item", // TODO specific plugin
    ].join(", "),
    exclude: ".s_showcase .row .row > div",
};

export function isMovable(el) {
    const canMoveUpOrDown = el.matches(moveUpOrDown.selector);
    const canMoveLeftOrRight =
        el.matches(moveLeftOrRight.selector) && !el.matches(moveLeftOrRight.exclude);
    return canMoveUpOrDown || canMoveLeftOrRight;
}

function getMoveDirection(el) {
    const canMoveVertically = el.matches(moveUpOrDown.selector);
    return canMoveVertically ? "vertical" : "horizontal";
}

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
        has_overlay_options: { hasOption: (el) => isMovable(el) },
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        on_clone_handlers: this.onClone.bind(this),
        on_remove_handlers: this.onRemove.bind(this),
    };

    setup() {
        this.overlayTarget = null;
        this.isMobileView = false;
        this.isGridItem = false;
    }

    getActiveOverlayButtons(target) {
        if (!isMovable(target)) {
            this.overlayTarget = null;
            return [];
        }

        const buttons = [];
        this.overlayTarget = target;
        this.refreshState();
        if (this.areArrowsDisplayed()) {
            if (this.hasPreviousSibling()) {
                const direction =
                    getMoveDirection(this.overlayTarget) === "vertical" ? "up" : "left";
                const button = {
                    class: `fa fa-fw fa-angle-${direction}`,
                    title: _t("Move %s", direction),
                    handler: this.onMoveClick.bind(this, "prev"),
                };
                buttons.push(button);
            }
            if (this.hasNextSibling()) {
                const direction =
                    getMoveDirection(this.overlayTarget) === "vertical" ? "down" : "right";
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

    onClone({ cloneEl, originalEl }) {
        if (!isMovable(originalEl)) {
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
        if (!isMovable(toRemoveEl)) {
            return;
        }
        // If there is a mobile order, the gap created by the removed element
        // must be filled in.
        const mobileOrder = toRemoveEl.style.order;
        if (mobileOrder) {
            fillRemovedItemGap(toRemoveEl.parentElement, parseInt(mobileOrder));
        }
    }

    refreshState() {
        this.isMobileView = isMobileView(this.overlayTarget);
        this.isGridItem = this.overlayTarget.classList.contains("o_grid_item");
    }

    // TODO check where to call it (SnippetMove > start).
    // refreshTarget() {
    //     // Needed for compatibility (with already dropped snippets).
    //     // If the target is a column, check if all the columns are either mobile
    //     // ordered or not. If they are not consistent, then we remove the mobile
    //     // order classes from all of them, to avoid issues.
    //     const parentEl = this.overlayTarget.parentElement;
    //     if (parentEl.classList.contains("row")) {
    //         const columnEls = [...parentEl.children];
    //         const orderedColumnEls = columnEls.filter((el) => el.style.order);
    //         if (orderedColumnEls.length && orderedColumnEls.length !== columnEls.length) {
    //             removeMobileOrders(orderedColumnEls);
    //         }
    //     }
    // }

    areArrowsDisplayed() {
        const siblingsEl = [...this.overlayTarget.parentNode.children];
        const visibleSiblingEl = siblingsEl.find(
            (el) => el !== this.overlayTarget && window.getComputedStyle(el).display !== "none"
        );
        // The arrows are not displayed if:
        // - the target is a grid item and not in mobile view
        // - the target has no visible siblings
        return !!visibleSiblingEl && !(this.isGridItem && !this.isMobileView);
    }

    hasPreviousSibling() {
        return !!getVisibleSibling(this.overlayTarget, "prev");
    }

    hasNextSibling() {
        return !!getVisibleSibling(this.overlayTarget, "next");
    }

    /**
     * Move the element in the given direction
     *
     * @param {String} direction "prev" or "next"
     */
    onMoveClick(direction) {
        // TODO nav-item ? (=> specific plugin)
        // const isNavItem = this.overlayTarget.classList.contains("nav-item");
        let hasMobileOrder = !!this.overlayTarget.style.order;
        const siblingEls = this.overlayTarget.parentNode.children;

        // If the target is a column, the ordering in mobile view is independent
        // from the desktop view. If we are in mobile view, we first add the
        // mobile order if there is none yet. In the case where we are not in
        // mobile view, the mobile order is reset.
        const parentEl = this.overlayTarget.parentNode;
        if (this.isMobileView && parentEl.classList.contains("row") && !hasMobileOrder) {
            addMobileOrders(siblingEls);
            hasMobileOrder = true;
        } else if (!this.isMobileView && hasMobileOrder) {
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

        // TODO scroll (data-no-scroll)
        // TODO update invisible dom
    }
}
