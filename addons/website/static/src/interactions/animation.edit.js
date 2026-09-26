import { Animation } from "./animation";
import { registry } from "@web/core/registry";

const AnimationEdit = (I) =>
    class extends I {
        // Overriding to keep "on appearance" animations reset in edit mode:
        // they are meant to play once on page load, not on every re-render.
        getIsResetting() {
            return !this.isAnimateOnScroll || super.getIsResetting();
        }

        startAnimation() {
            if (!this.isAnimateOnScroll) {
                return;
            }
            super.startAnimation();
        }

        destroy() {
            // We remove the "o_animate_preview" class here because it is added
            // when an animation is selected in the options, and the "Animation"
            // interaction considers it as part of the initial state. We remove
            // it here because otherwise it is added back when exiting edit
            // mode.
            this.el.classList.remove("o_animate_preview");
            // An inline "animation-name" is only ever a way to restart an
            // animation ("dummy" in "forceAnimation", "dummy-none" in the
            // "Animation" interaction), never a configuration to keep. If the
            // interaction happened to start while one was set, it was taken as
            // the initial state and has just been restored: it would otherwise
            // be saved along with the element.
            this.el.style.removeProperty("animation-name");
        }
    };

registry.category("public.interactions.edit").add("website.animation", {
    Interaction: Animation,
    mixin: AnimationEdit,
});
