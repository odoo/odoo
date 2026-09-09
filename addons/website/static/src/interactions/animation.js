/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { getScrollingElement, isScrollableY } from "@web/core/utils/dom/scrolling";
import { isVisible } from "@web/core/utils/dom/ui";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.animation");

// Several `.o_animate` elements can finish their animation within the same
// frame; coalesce their "animationend" reaction into a single global resize
// dispatch per frame instead of one per element.
let resizeDispatchScheduled = false;
function scheduleGlobalResizeDispatch() {
    if (resizeDispatchScheduled) {
        return;
    }
    resizeDispatchScheduled = true;
    window.requestAnimationFrame(() => {
        resizeDispatchScheduled = false;
        window.dispatchEvent(new Event("resize"));
    });
}

export class Animation extends Interaction {
    static selector = ".o_animate";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _scrollingTarget: () => this.scrollingTarget,
        _windowUnlessDropdown: () => this.windowUnlessDropdown,
    };
    dynamicContent = {
        _window: { "t-on-resize": this.throttled(this.scrollWebsiteAnimate) },
        _windowUnlessDropdown: {
            "t-on-shown.bs.modal": this.scrollWebsiteAnimate,
            "t-on-slid.bs.carousel": this.scrollWebsiteAnimate,
            "t-on-shown.bs.tab": this.scrollWebsiteAnimate,
            "t-on-shown.bs.collapse": this.scrollWebsiteAnimate,
        },
        _scrollingTarget: {
            "t-on-scroll.capture": this.throttled(this.scrollWebsiteAnimate),
        },
        _root: {
            "t-att-class": (el) => ({
                o_animating: this.isAnimating,
                o_animated: this.isAnimated,
                o_animate_in_dropdown: !!el.closest(".dropdown"),
                o_animate_preview: undefined,
            }),
            "t-att-style": (el) => {
                const result = {
                    "animation-name": this.isResetting ? "dummy-none" : undefined,
                    "animation-play-state":
                        this.isResetting || this.isAnimateOnScroll
                            ? undefined
                            : this.playState,
                    visibility: "visible",
                };
                if (this.isAnimateOnScroll) {
                    result["animation-delay"] = this.delay;
                }
                return result;
            },
        },
    };

    offsetRatio = 0.3;
    offsetMin = 10;

    setup() {
        this.wrapwrapEl = document.querySelector("#wrapwrap");
        this.windowUnlessDropdown = this.el.closest(".dropdown") ? [] : window;
        this.scrollingElement = this.findScrollingElement();
        this.scrollingTarget = isScrollableY(this.scrollingElement)
            ? this.scrollingElement
            : this.scrollingElement.ownerDocument.defaultView;
        this.isAnimating = false;
        this.isAnimated = false;
        this.isAnimateOnScroll = this.el.classList.contains("o_animate_on_scroll");
        this.isResetting = false;
        const style = window.getComputedStyle(this.el);
        this.playState = style.animationPlayState;
        this.delay = undefined;
        log.lifecycle("Animation setup", () => ({
            className: this.el.className,
            isAnimateOnScroll: this.isAnimateOnScroll,
            inDropdown: Array.isArray(this.windowUnlessDropdown),
            scrollingTargetIsElement: this.scrollingTarget === this.scrollingElement,
            playState: this.playState,
        }));
    }

    start() {
        if (this.el.closest(".dropdown")) {
            log.logic("Animation start: inside dropdown, skip", () => ({
                className: this.el.className,
            }));
            return;
        }
        if (!this.isAnimateOnScroll) {
            log.logic("Animation start: reset before first scroll check", () => ({
                className: this.el.className,
            }));
            this.resetAnimation();
            this.updateContent();
        }
        this.scrollWebsiteAnimate();
        this.updateContent();
    }

    findScrollingElement() {
        return getScrollingElement(this.el.ownerDocument);
    }

    startAnimation() {
        this.waitForTimeout(() => {
            this.isAnimating = true;
            this.playState = "running";
            for (const eventName of [
                "webkitAnimationEnd",
                "oanimationend",
                "msAnimationEnd",
                "animationend",
            ]) {
                this.addListener(
                    this.el,
                    eventName,
                    () => {
                        log.lifecycle("Animation ended", () => ({
                            eventName,
                            className: this.el.className,
                        }));
                        this.isAnimating = false;
                        this.isAnimated = true;
                        scheduleGlobalResizeDispatch();
                    },
                    { once: true },
                );
            }
        });
    }

    resetAnimation() {
        this.isResetting = true;
        this.isAnimated = false;
        this.isAnimating = false;
        this.updateContent();
        void this.el.offsetWidth;
        this.isResetting = false;
        this.playState = "paused";
    }

    /**
     * @param {HTMLElement} el
     * @param {HTMLElement} [topEl]
     */
    getElementOffsetTop(el, topEl) {
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
        const elOffset = this.isAnimateOnScroll
            ? 0
            : Math.max(elHeight * this.offsetRatio, this.offsetMin);

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
        if (footerEl && this.wrapwrapEl.classList.contains("o_footer_effect_enable")) {
            const actualScroll = scrollTop + windowsHeight;
            const totalScrollHeight = this.wrapwrapEl.scrollHeight;
            const heightFromFooter = this.getElementOffsetTop(el, footerEl);
            visible =
                actualScroll >=
                totalScrollHeight - heightFromFooter - elHeight + elOffset;
        } else {
            visible =
                windowsHeight > elTop + elOffset && 0 < elTop + elHeight - elOffset;
        }
        if (this.isAnimateOnScroll) {
            if (visible) {
                const start = 100 / (parseFloat(el.dataset.scrollZoneStart) || 1);
                const end = 100 / (parseFloat(el.dataset.scrollZoneEnd) || 1);
                const out = el.classList.contains("o_animate_out");
                const ratio =
                    (out ? elTop + elHeight : elTop) /
                    (windowsHeight - windowsHeight / start);
                const duration = parseFloat(
                    window.getComputedStyle(el).animationDuration,
                );
                const delay = (ratio - 1) * (duration * end);
                this.delay = (out ? -duration - delay : delay) + "s";
                this.isAnimating = true;
            } else if (el.classList.contains("o_animating")) {
                this.isAnimating = false;
            }
        } else {
            if (visible && this.playState === "paused") {
                log.pipeline("Animation scroll: paused -> start", () => ({
                    className: el.className,
                    elTop,
                    scrollTop,
                }));
                el.classList.add("o_visible");
                this.startAnimation();
            } else if (
                !visible &&
                el.classList.contains("o_animate_both_scroll") &&
                this.playState === "running"
            ) {
                log.pipeline("Animation scroll: running -> reset", () => ({
                    className: el.className,
                    elTop,
                    scrollTop,
                }));
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
