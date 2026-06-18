import { Animation } from "./animation";
import { registry } from "@web/core/registry";

const AnimationEdit = I => class extends I {
    destroy() {
        // We remove the "o_animate_preview" and "o_animating" classes here
        // because they are added when an animation is selected in the options,
        // and the "Animation" interaction considers it as part of the initial
        // state. We remove it here because otherwise it is added back when
        // exiting edit mode.
        this.el.classList.remove("o_animate_preview", "o_animating");
    }

    getConfigurationSnapshot() {
        // Only the animation mode impacts the interaction state after it has
        // started. Effect classes and CSS variables can change without a
        // restart because they are read by the browser when replaying the
        // animation.
        return JSON.stringify({
            isAnimateOnScroll: this.el.classList.contains("o_animate_on_scroll"),
            isAnimateOnScrollOut: this.el.classList.contains("o_animate_out"),
            isAnimateBothScroll: this.el.classList.contains("o_animate_both_scroll"),
        });
    }
};

registry
    .category("public.interactions.edit")
    .add("website.animation", {
        Interaction: Animation,
        mixin: AnimationEdit,
    });
