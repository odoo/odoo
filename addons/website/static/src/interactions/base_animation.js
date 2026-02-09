import { Interaction } from "@web/public/interaction";

import { getScrollingElement, isScrollableY } from "@web/core/utils/scrolling";
import { isVisible } from "@web/core/utils/ui";

export class BaseAnimation extends Interaction {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _scrollingTarget: () => this.scrollingTarget,
        _windowUnlessDropdown: () => this.windowUnlessDropdown,
    };
    dynamicContent = {
        _window: { "t-on-resize": this.scrollWebsiteAnimate },
        _windowUnlessDropdown: {
            "t-on-shown.bs.modal": this.scrollWebsiteAnimate,
            "t-on-slid.bs.carousel": this.scrollWebsiteAnimate,
            "t-on-shown.bs.tab": this.scrollWebsiteAnimate,
            "t-on-shown.bs.collapse": this.scrollWebsiteAnimate,
        },
    };

    offsetRatio = 0.3; // Dynamic offset ratio: 0.3 = (element's height/3)
    offsetMin = 10; // Minimum offset for small elements (in pixels)

    setup() {
        this.wrapwrapEl = document.querySelector("#wrapwrap");
        this.windowUnlessDropdown = this.el.closest(".dropdown") ? [] : window;
        this.scrollingElement = this.findScrollingElement();
        this.scrollingTarget = isScrollableY(this.scrollingElement)
            ? this.scrollingElement
            : this.scrollingElement.ownerDocument.defaultView;
        this.delay = undefined;
        this.targetEl = this.el;
    }

    findScrollingElement() {
        return getScrollingElement(this.el.ownerDocument);
    }

    /**
     * Starts animation and/or update element's state.
     */
    startAnimation() {}

    /**
     * Gets element top offset by not taking CSS transforms into calculations.
     *
     * @param {HTMLElement} el
     * @param {HTMLElement} [topEl] if specified, calculates the top distance to
     *     this element.
     */
    getElementOffsetTop(el, topEl) {
        // Loop through the DOM tree and add its parent's offset to get page offset.
        let top = 0;
        do {
            top += el.offsetTop || 0;
            el = el.offsetParent;
            if (topEl && el === topEl) {
                return top;
            }
        } while (el);
        return top;
    }

    scrollWebsiteAnimate() {
        const el = this.targetEl;
        if (el.classList.contains("o_animate_in_dropdown")) {
            return;
        }
        const windowsHeight = window.innerHeight;
        const elHeight = el.offsetHeight;
        const elOffset = this.isAnimateOnScroll
            ? 0
            : Math.max(elHeight * this.offsetRatio, this.offsetMin);

        // We need to offset for the change in position from some animation.
        // So we get the top value by not taking CSS transforms into calculations.
        // Cookies bar might be opened and considered as a modal but it is
        // not really one when there is no backdrop (eg 'discrete' layout),
        // and should not be used as scrollTop value.
        const closestModal = el.closest(".modal");
        let scrollTop = this.scrollingElement.scrollTop;
        if (closestModal && isVisible(closestModal)) {
            scrollTop = closestModal.classList.contains("s_popup_no_backdrop")
                ? closestModal.querySelector(".modal-content").scrollTop
                : closestModal.scrollTop;
        }
        const elTop = this.getElementOffsetTop(el) - scrollTop;
        let visible;
        const footerEl = el.closest(".o_footer_slideout");
        if (footerEl) {
            // Since the footer slideout is always in the viewport but not
            // always displayed, the way to calculate if an element is
            // visible in the footer is different. We decided to handle this
            // case specifically instead of a generic solution using
            // elementFromPoint as it is a rare case and the implementation
            // would have been too complicated for such a small use case.
            const actualScroll = scrollTop + windowsHeight;
            const totalScrollHeight = this.wrapwrapEl.scrollHeight;
            const heightFromFooter = this.getElementOffsetTop(el, footerEl);
            visible = actualScroll >= totalScrollHeight - heightFromFooter - elHeight + elOffset;
        } else {
            visible = windowsHeight > elTop + elOffset && 0 < elTop + elHeight - elOffset;
        }
        return { visible, elTop, elHeight, windowsHeight };
    }
}
