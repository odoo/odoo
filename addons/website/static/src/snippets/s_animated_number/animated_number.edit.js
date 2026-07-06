import { registry } from "@web/core/registry";
import { AnimatedNumber } from "./animated_number";

export const AnimatedNumberEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.stopAnimation = this._stopAnimation.bind(this);
        }

        start() {
            super.start();
            this.addListener(this.el, "click", this.stopAnimation, { once: true });
        }

        _stopAnimation() {
            this.forcedStop = true;
        }
    };

registry.category("public.interactions.edit").add("website.animated_number", {
    Interaction: AnimatedNumber,
    mixin: AnimatedNumberEdit,
});
