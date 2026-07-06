import { registry } from "@web/core/registry";
import { AnimatedNumber } from "./animated_number";

export const AnimatedNumberEdit = (I) =>
    class extends I {
        start() {
            super.start();
            this.addListener(this.el, "click", () => (this.forcedStop = true), { once: true });
        }

        getConfigurationSnapshot() {
            const style = getComputedStyle(this.el);
            return JSON.stringify({
                startValue: this.el.dataset.startValue,
                endValue: this.el.dataset.endValue,
                animationDelay: style.animationDelay,
                animationDuration: style.animationDuration,
            });
        }
    };

registry.category("public.interactions.edit").add("website.animated_number", {
    Interaction: AnimatedNumber,
    mixin: AnimatedNumberEdit,
});
