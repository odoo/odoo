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
        // No need to scroll when target is _blank as it should open a new tab
        if (!anchorEl || !scrollValue || this.el.target === "_blank") {
            return;
        }

        this.manageScroll(hash, anchorEl, scrollValue);
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
