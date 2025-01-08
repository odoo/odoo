import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { getScrollingElement, isScrollableY } from "@web/core/utils/scrolling";
import { isVisible } from "@web/core/utils/ui";

export class Animation extends Interaction {
    static selector = ".o_animate";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _wrapwrap: () => this.wrapwrapEl,
        _scrollingTarget: () => this.scrollingTarget,
    };
    dynamicContent = {
        _window: {
            "t-on-resize": this.scrollWebsiteAnimate,
        },
        _wrapwrap: {
            "t-on-shown.bs.modal": this.scrollWebsiteAnimate,
            "t-on-slid.bs.carousel": this.scrollWebsiteAnimate,
            "t-on-shown.bs.tab": this.scrollWebsiteAnimate,
            "t-on-shown.bs.collapse": this.scrollWebsiteAnimate,
        },
        _scrollingTarget: {
            // Setting capture to true allows to take advantage of event
            // bubbling for events that otherwise don’t support it. (e.g. useful
            // when scrolling a modal)
            "t-on-scroll.capture": this.throttledForAnimation(this.scrollWebsiteAnimate),
        },
        _root: {
            "t-att-class": (el) => ({
                "o_animating": this.isAnimating,
                "o_animated": this.isAnimated,
                "o_animate_in_dropdown": !!el.closest(".dropdown"),
                // TODO Remove with edit mode
                "o_animate_preview": undefined,
            }),
            "t-att-style": (el) => {
                return {
                    "animation-name": this.isResetting ? "dummy-none" : undefined,
                    "animation-play-state": (this.isResetting || this.isAnimateOnScroll) ? undefined : this.playState,
                    "animation-delay": this.delay,
                    // The ones which are invisible in state 0 (like fade_in for
                    // example) will stay invisible.
                    "visibility": "visible",
                };
            },
        },
    };

    offsetRatio = 0.3; // Dynamic offset ratio: 0.3 = (element's height/3)
    offsetMin = 10; // Minimum offset for small elements (in pixels)

    setup() {
        this.wrapwrapEl = document.querySelector("#wrapwrap");
        this.scrollingElement = getScrollingElement(this.el.ownerDocument);
        this.scrollingTarget = isScrollableY(this.scrollingElement) ? this.scrollingElement : this.scrollingElement.ownerDocument.defaultView;
        this.isAnimating = false;
        this.isAnimated = false;
        this.isAnimateOnScroll = this.el.classList.contains("o_animate_on_scroll");
        this.isResetting = false;
        const style = window.getComputedStyle(this.el);
        this.playState = style.animationPlayState;
        this.delay = undefined;
    }

    start() {
        // By default, elements are hidden by the css of o_animate.
        // Render elements and trigger the animation then pause it in state 0.
        if (!this.el.closest(".dropdown") && !this.isAnimateOnScroll) {
            this.resetAnimation();
            this.updateContent();
        }
    }

    /**
     * Starts animation and/or update element's state.
     */
    startAnimation() {
        // Forces the browser to redraw using setTimeout.
        this.waitForTimeout(() => {
            this.isAnimating = true;
            this.playState = "running";
            for (const eventName of ["webkitAnimationEnd", "oanimationend", "msAnimationEnd", "animationend"]) {
                this.addListener(this.el, eventName, () => {
                    this.isAnimating = false;
                    this.isAnimated = true;
                    window.dispatchEvent(new Event("resize"));
                }, { once: true });
            }
        });
    }

    resetAnimation() {
        this.isResetting = true;
        this.isAnimated = false;
        this.isAnimating = false;
        this.updateContent();
        // trigger a DOM reflow
        void this.el.offsetWidth;
        this.isResetting = false;
        this.playState = "paused";
    }

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
        const el = this.el;
        if (el.classList.contains("o_animate_in_dropdown")) {
            return;
        }
        const windowsHeight = window.innerHeight;
        const elHeight = el.offsetHeight;
        let elOffset = this.isAnimateOnScroll ? 0 : Math.max((elHeight * this.offsetRatio), this.offsetMin);

        // We need to offset for the change in position from some animation.
        // So we get the top value by not taking CSS transforms into calculations.
        // Cookies bar might be opened and considered as a modal but it is
        // not really one when there is no backdrop (eg 'discrete' layout),
        // and should not be used as scrollTop value.
        const closestModal = el.closest(".modal");
        let scrollTop = this.scrollingElement.scrollTop;
        if (closestModal && isVisible(closestModal)) {
            scrollTop = closestModal.classList.contains("s_popup_no_backdrop") ?
                closestModal.querySelector(".modal-content").scrollTop :
                closestModal.scrollTop;
        }
        const elTop = this.getElementOffsetTop(el) - scrollTop;
        let visible;
        const footerEl = el.closest(".o_footer_slideout");
        if (footerEl && this.wrapwrapEl.classList.contains("o_footer_effect_enable")) {
            // Since the footer slideout is always in the viewport but not
            // always displayed, the way to calculate if an element is
            // visible in the footer is different. We decided to handle this
            // case specifically instead of a generic solution using
            // elementFromPoint as it is a rare case and the implementation
            // would have been too complicated for such a small use case.
            const actualScroll = this.wrapwrapEl.scrollTop + windowsHeight;
            const totalScrollHeight = this.wrapwrapEl.scrollHeight;
            const heightFromFooter = this.getElementOffsetTop(el, footerEl);
            visible = actualScroll >=
                totalScrollHeight - heightFromFooter - elHeight + elOffset;
        } else {
            visible = windowsHeight > (elTop + elOffset) &&
                0 < (elTop + elHeight - elOffset);
        }
        if (this.isAnimateOnScroll) {
            if (visible) {
                const start = 100 / (parseFloat(el.dataset.scrollZoneStart) || 1);
                const end = 100 / (parseFloat(el.dataset.scrollZoneEnd) || 1);
                const out = el.classList.contains('o_animate_out');
                const ratio = (out ? elTop + elHeight : elTop) / (windowsHeight - (windowsHeight / start));
                const duration = parseFloat(window.getComputedStyle(el).animationDuration);
                const delay = (ratio - 1) * (duration * end);
                this.delay = (out ? - duration - delay : delay) + "s";
                this.isAnimating = true;
            } else if (el.classList.contains("o_animating")) {
                this.isAnimating = false;
            }
        } else {
            if (visible && this.playState === "paused") {
                el.classList.add("o_visible");
                this.startAnimation();
            } else if (!visible && el.classList.contains("o_animate_both_scroll") && this.playState === "running") {
                el.classList.remove("o_visible");
                this.resetAnimation();
            }
        }
    }

    updateContent() {
        super.updateContent();
        this.el.dispatchEvent(new Event("updatecontent", { bubbles: true }));
    }
}

registry.category("public.interactions").add("website.animation", Animation);

registry
    .category("public.interactions.edit")
    .add("website.animation", {
        Interaction: Animation,
    });
