import { BaseAnimation } from "./base_animation";
import { registry } from "@web/core/registry";

export class Animation extends BaseAnimation {
    static selector = ".o_animate";
    dynamicContent = {
        ...this.dynamicContent,
        _scrollingTarget: {
            // Setting capture to true allows to take advantage of event
            // bubbling for events that otherwise don’t support it. (e.g. useful
            // when scrolling a modal)
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
                        this.isResetting || this.isAnimateOnScroll ? undefined : this.playState,
                    // The ones which are invisible in state 0 (like fade_in for
                    // example) will stay invisible.
                    visibility: "visible",
                };
                // Avoid resetting animation-delay upon stop when it is not
                // supposed to be modified at all.
                if (this.isAnimateOnScroll) {
                    result["animation-delay"] = this.delay;
                }
                return result;
            },
        },
    };

    setup() {
        super.setup();

        this.isAnimating = false;
        this.isAnimated = false;
        this.isAnimateOnScroll = this.el.classList.contains("o_animate_on_scroll");
        this.isResetting = false;
        const style = window.getComputedStyle(this.el);
        this.playState = style.animationPlayState;
        this.delay = undefined;
    }

    start() {
        if (this.el.closest(".dropdown")) {
            return;
        }
        // By default, elements are hidden by the css of o_animate.
        // Render elements and trigger the animation then pause it in state 0.
        if (!this.isAnimateOnScroll) {
            this.resetAnimation();
            this.updateContent();
        }
        this.scrollWebsiteAnimate();
        this.updateContent();
    }

    /**
     * Starts animation and/or update element's state.
     */
    startAnimation() {
        // Forces the browser to redraw using setTimeout.
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
                        this.isAnimating = false;
                        this.isAnimated = true;
                        window.dispatchEvent(new Event("resize"));
                    },
                    { once: true }
                );
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

    scrollWebsiteAnimate() {
        const el = this.targetEl;
        const { visible, elTop, elHeight, windowsHeight } = super.scrollWebsiteAnimate();
        if (this.isAnimateOnScroll) {
            if (visible) {
                const start = 100 / (parseFloat(el.dataset.scrollZoneStart) || 1);
                const end = 100 / (parseFloat(el.dataset.scrollZoneEnd) || 1);
                const out = el.classList.contains("o_animate_out");
                const ratio =
                    (out ? elTop + elHeight : elTop) / (windowsHeight - windowsHeight / start);
                const duration = parseFloat(window.getComputedStyle(el).animationDuration);
                const delay = (ratio - 1) * (duration * end);
                this.delay = (out ? -duration - delay : delay) + "s";
                this.isAnimating = true;
            } else if (el.classList.contains("o_animating")) {
                this.isAnimating = false;
            }
        } else {
            if (visible && this.playState === "paused") {
                el.classList.add("o_visible");
                this.startAnimation();
            } else if (
                !visible &&
                el.classList.contains("o_animate_both_scroll") &&
                this.playState === "running"
            ) {
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
