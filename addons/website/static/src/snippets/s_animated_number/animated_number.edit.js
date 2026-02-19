import { registry } from "@web/core/registry";
import { AnimatedNumber } from "./animated_number";

export const AnimatedNumberEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.forceStopBinded = this.forceStop.bind(this);

            this.el.addEventListener("click", this.forceStopBinded);
            this.registerCleanup(() => this.el.removeEventListener("click", this.forceStopBinded));
        }
        forceStop() {
            this.forcedStop = true;
        }
    };

registry.category("public.interactions.edit").add("website.animated_number", {
    Interaction: AnimatedNumber,
    mixin: AnimatedNumberEdit,
});
