/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { isScrollableY } from "@web/core/utils/dom/scrolling";
import { Modal } from "@web/libs/bootstrap";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.no_backdrop_popup");

export class NoBackdropPopup extends Interaction {
    static selector = ".s_popup_no_backdrop";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": this.addModalNoBackdropEvents,
            "t-on-hide.bs.modal": this.removeModalNoBackdropEvents,
        },
    };

    setup() {
        log.lifecycle("NoBackdropPopup setup", () => ({ id: this.el.id }));
        this.throttledUpdateScrollbar = this.throttled(this.updateScrollbar);
        this.removeResizeListener = null;
        this.resizeObserver = null;
    }

    destroy() {
        log.lifecycle("NoBackdropPopup destroy", () => ({ id: this.el.id }));
        this.removeModalNoBackdropEvents();
        window.dispatchEvent(new Event("resize"));
    }

    updateScrollbar() {
        const modalContentEl = this.el.querySelector(".modal-content");
        const isOverflowing = isScrollableY(modalContentEl);
        const bsModal = Modal.getOrCreateInstance(this.el);
        // Bootstrap locks the page behind every modal; without a backdrop the
        // page stays usable, so the lock is given back unless the popup's own
        // content scrolls, since two scrollbars stacked leave the inner one
        // unreachable. The body class tells which state Bootstrap's helper is
        // in: hiding an already hidden overflow would save "hidden" as the
        // value to restore.
        const locked = document.body.classList.contains("modal-open");
        if (isOverflowing && !locked) {
            bsModal._scrollBar.hide();
            document.body.classList.add("modal-open");
        } else if (!isOverflowing && locked) {
            bsModal._scrollBar.reset();
            document.body.classList.remove("modal-open");
        }
        log.logic("updateScrollbar", () => ({ id: this.el.id, isOverflowing, locked }));
        if (isOverflowing) {
            bsModal._adjustDialog();
        } else {
            bsModal._resetAdjustments();
        }
    }

    addModalNoBackdropEvents() {
        this.updateScrollbar();
        this.removeResizeListener = this.addListener(
            window,
            "resize",
            this.throttledUpdateScrollbar,
        );
        this.resizeObserver = new window.ResizeObserver(() => {
            this.updateScrollbar();
        });
        this.resizeObserver.observe(this.el.querySelector(".modal-content"));
        log.lifecycle("NoBackdropPopup resize listener and observer attached", () => ({
            id: this.el.id,
        }));
    }

    removeModalNoBackdropEvents() {
        this.throttledUpdateScrollbar.cancel();
        if (this.resizeObserver) {
            this.removeResizeListener();
            this.resizeObserver.disconnect();
            delete this.resizeObserver;
            log.lifecycle(
                "NoBackdropPopup resize listener and observer removed",
                () => ({
                    id: this.el.id,
                }),
            );
        }
    }
}

registry
    .category("public.interactions")
    .add("website.no_backdrop_popup", NoBackdropPopup);
