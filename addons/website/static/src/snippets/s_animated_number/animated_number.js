import { BaseAnimation } from "@website/interactions/base_animation";
import { registry } from "@web/core/registry";
import { firstLeaf } from "@html_editor/utils/dom_traversal";

export class AnimatedNumber extends BaseAnimation {
    static selector = ".s_animated_number";
    dynamicContent = {
        ...this.dynamicContent,
        _document: {
            // Setting capture to true allows to take advantage of event
            // bubbling for events that otherwise don’t support it. (e.g. useful
            // when scrolling a modal)
            "t-on-scroll.capture": this.throttled(this.scrollWebsiteAnimate),
        },
    };

    setup() {
        super.setup();

        const dataset = this.el.dataset;
        this.startValue = parseInt(dataset.startValue);
        this.endValue = parseInt(dataset.endValue);
        this.startAfter = parseInt(this.el.style.animationDelay) * 1000 || 0;
        this.duration = parseInt(this.el.style.animationDuration) * 1000 || 1000;

        this.scrollingElement = this.el.ownerDocument.scrollingElement;
        this.waiting = true;
        this.forcedStop = false;

        let numberEl = this.el.querySelector(".s_animated_number_value");
        if (!numberEl) {
            return;
        }
        numberEl = firstLeaf(numberEl, (el) => el.childNodes.length != 1);
        numberEl.textContent = this.startValue;
        this.numberEl = numberEl;
    }

    start() {
        if (this.el.closest(".dropdown")) {
            return;
        }
        this.scrollWebsiteAnimate();
    }

    scrollWebsiteAnimate() {
        if (!this.waiting) {
            return;
        }
        const { visible } = super.scrollWebsiteAnimate();
        if (visible) {
            this.startAnimation();
        }
    }

    startAnimation() {
        this.waiting = false;

        const numberEl = this.numberEl;
        if (!numberEl) {
            return;
        }

        const startValue = this.startValue;
        const endValue = this.endValue;
        const duration = this.duration;

        this.waitForTimeout(() => {
            const startTime = performance.now();

            function animate() {
                if (this.forcedStop) {
                    numberEl.textContent = endValue;
                    return;
                }

                const elapsed = performance.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easedProgress = 1 - Math.pow(1 - progress, 3);
                const value = startValue + (endValue - startValue) * easedProgress;

                numberEl.textContent = Math.round(value);

                if (progress < 1) {
                    this.waitForAnimationFrame(animate);
                }
            }

            this.waitForAnimationFrame(animate);
        }, this.startAfter);
    }
}

registry.category("public.interactions").add("website.animated_number", AnimatedNumber);
