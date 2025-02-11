import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { isScrollableY } from "@web/core/utils/scrolling";

export class NoBackdropPopup extends Interaction {
    static selector = ".s_popup_no_backdrop";
    dynamicContent = {
        "_root": {
            "t-on-shown.bs.modal": this.addModalNoBackdropEvents,
            "t-on-hide.bs.modal": this.removeModalNoBackdropEvents,
        }
    };

    setup() {
        this.throttledUpdateScrollbar = this.throttled(this.updateScrollbar);
        this.removeResizeListener = null;
        this.resizeObserver = null;
    }

    destroy() {
        this.removeModalNoBackdropEvents();
        // After destroying the interaction, we need to trigger a resize event
        // so that the scrollbar can adjust to its default behavior.
        window.dispatchEvent(new Event("resize"));
    }

    updateScrollbar() {
        // When there is no backdrop the element with the scrollbar is
        // '.modal-content' (see comments in CSS).
        const modalContentEl = this.el.querySelector(".modal-content");
        const isOverflowing = isScrollableY(modalContentEl);
        const bsModal = window.Modal.getOrCreateInstance(this.el);
        if (isOverflowing) {
            // If the "no-backdrop" modal has a scrollbar, the page's scrollbar
            // must be hidden. This is because if the two scrollbars overlap, it
            // is no longer possible to scroll using the modal's scrollbar.
            bsModal._adjustDialog();
        } else {
            // If the "no-backdrop" modal does not have a scrollbar, the page
            // scrollbar must be displayed because we must be able to scroll the
            // page (e.g. a "cookies bar" popup at the bottom of the page must
            // not prevent scrolling the page).
            bsModal._resetAdjustments();
        }
    }

    addModalNoBackdropEvents() {
        this.updateScrollbar();
        this.removeResizeListener = this.addListener(window, "resize", this.throttledUpdateScrollbar);
        this.resizeObserver = new window.ResizeObserver(() => {
            // When the size of the modal changes, the scrollbar needs to be
            // adjusted.
            this.updateScrollbar();
        });
        this.resizeObserver.observe(this.el.querySelector(".modal-content"));
    }

    removeModalNoBackdropEvents() {
        this.throttledUpdateScrollbar.cancel();
        if (this.resizeObserver) {
            this.removeResizeListener();
            this.resizeObserver.disconnect();
            delete this.resizeObserver;
        }
    }
}

registry
    .category("public.interactions")
    .add("website.no_backdrop_popup", NoBackdropPopup);
