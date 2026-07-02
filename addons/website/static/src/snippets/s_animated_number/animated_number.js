import { BaseAnimation } from "@website/interactions/base_animation";
import { registry } from "@web/core/registry";

export class AnimatedNumber extends BaseAnimation {
    static selector = ".s_animated_number";

    setup() {
        super.setup();

        const dataset = this.el.dataset;
        this.startValue = parseInt(dataset.startValue);
        this.endValue = parseInt(dataset.endValue);

        const style = window.getComputedStyle(this.el);
        this.startAfter = parseFloat(style.animationDelay) * 1000 || 0;
        this.duration = parseFloat(style.animationDuration) * 1000 || 1000;

        this.alreadyStarted = false;
        this.forcedStop = false;

        const numberEl = this.el.querySelector(".s_animated_number_value");
        numberEl.textContent = this.startValue;
        this.numberEl = numberEl;
    }

    start() {
        this.scrollWebsiteAnimate();
    }

    scrollWebsiteAnimate() {
        if (this.alreadyStarted) {
            return;
        }
        const { visible } = super.scrollWebsiteAnimate();
        if (visible) {
            this.startAnimation();
        }
    }

    startAnimation() {
        this.alreadyStarted = true;

        const numberEl = this.numberEl;
        if (!numberEl) {
            return;
        }

        const startValue = this.startValue;
        const endValue = this.endValue;
        const duration = this.duration;

        if (window.matchMedia(`(prefers-reduced-motion: reduce)`).matches) {
            numberEl.textContent = endValue;
        } else {
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
}

registry.category("public.interactions").add("website.animated_number", AnimatedNumber);
