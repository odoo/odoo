import { scrollTo } from "@html_builder/utils/scrolling";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class AnchorSlide extends Interaction {
    static selector = "a[href^='/'][href*='#'], a[href^='#']";
    dynamicContent = {
        _root: {
            "t-on-click": this.animateClick,
        },
    };

    setup() {
        /**
         * It expands the corresponding accordion item if the target element
         * matches the hash.
         */
        const hash = window.location.hash.substring(1);
        const anchorEl = document.getElementById(hash);
        if (anchorEl && anchorEl.classList.contains("accordion-item")) {
            this.handleAccordionAnchor(anchorEl);
        }
    }

    /**
     * @param {HTMLElement} el the element to scroll to.
     * @param {string} [scrollValue='true'] scroll value
     * @returns {Promise}
     */
    scrollTo(el, scrollValue = "true") {
        return scrollTo(el, {
            duration: scrollValue === "true" ? 500 : 0,
            extraOffset: this.computeExtraOffset(),
        });
    }

    computeExtraOffset() {
        return 0;
    }

    /**
     * Automatically opens the specific accordion item and closes the others.
     *
     * @param {HTMLElement} anchorEl - The accordion item element to handle.
     */
    handleAccordionAnchor(anchorEl) {
        const accordionCollapseEl = anchorEl.querySelector(".accordion-collapse");
        Collapse.getOrCreateInstance(accordionCollapseEl, {
            toggle: false,
        }).show();
    }

    /**
     * @param {MouseEvent} ev
     */
    animateClick(ev) {
        const ensureSlash = (path) => (path.endsWith("/") ? path : path + "/");
        if (ensureSlash(this.el.pathname) !== ensureSlash(window.location.pathname)) {
            return;
        }
        // Avoid flicker at destination in case of ending "/" difference.
        if (this.el.pathname !== window.location.pathname) {
            this.el.pathname = window.location.pathname;
        }
        let hash = this.el.hash;
        if (!hash.length) {
            return;
        }
        // Escape special characters to make the selector work.
        hash = "#" + CSS.escape(hash.substring(1));
        const anchorEl = this.el.ownerDocument.querySelector(hash);
        const scrollValue = anchorEl?.dataset.anchor;
        // No need to scroll when target is _blank as it should open in new tab
        if (!anchorEl || !scrollValue || this.el.target === "_blank") {
            return;
        }

        if (anchorEl.classList.contains("accordion-item")) {
            this.handleAccordionAnchor(anchorEl);
        }
        const offcanvasEl = this.el.closest(".offcanvas.o_navbar_mobile");
        if (offcanvasEl && offcanvasEl.classList.contains("show")) {
            // Special case for anchors in offcanvas in mobile: we can't just
            // scrollTo() after preventDefault because preventDefault would
            // prevent the offcanvas to be closed. The choice is then to close
            // it ourselves manually and once it's fully closed, then start our
            // own smooth scrolling.
            ev.preventDefault();
            Offcanvas.getInstance(offcanvasEl).hide();
            this.addListener(
                offcanvasEl,
                "hidden.bs.offcanvas",
                () => this.manageScroll(hash, anchorEl, scrollValue),
                // the listener must be automatically removed when invoked
                { once: true }
            );
        } else {
            ev.preventDefault();
            this.manageScroll(hash, anchorEl, scrollValue);
        }
    }

    /**
     * @param {string} hash
     * @param {HTMLElement} anchorEl the element to scroll to.
     * @param {string} [scrollValue='true'] scroll value
     */
    manageScroll(hash, anchorEl, scrollValue = "true") {
        if (hash === "#top" || hash === "#bottom") {
            // If the anchor targets #top or #bottom, directly call the
            // "scrollTo" function. The reason is that the header or the footer
            // could have been removed from the DOM. By receiving a string as
            // parameter, the "scrollTo" function handles the scroll to the top
            // or to the bottom of the document even if the header or the
            // footer is removed from the DOM.
            this.scrollTo(hash);
        } else {
            this.scrollTo(anchorEl, scrollValue);
        }
    }
}

registry.category("public.interactions").add("website.anchor_slide", AnchorSlide);
