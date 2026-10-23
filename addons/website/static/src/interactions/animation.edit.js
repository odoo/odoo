import { Animation } from "./animation";
import { registry } from "@web/core/registry";

const AnimationEdit = (I) =>
    class extends I {
        start() {
            if (!this.el.closest(".dropdown")) {
                return super.start();
            }
            if (this.el.closest(".dropdown-menu.show")) {
                this.resetAnimation();
                this.updateContent();
                this.startAnimation();
            }
        }

        destroy() {
            // We remove the "o_animate_preview" class here because it is added
            // when an animation is selected in the options, and the "Animation"
            // interaction considers it as part of the initial state. We remove
            // it here because otherwise it is added back when exiting edit
            // mode.
            this.el.classList.remove("o_animate_preview");
        }

        getConfigurationSnapshot() {
            // Restart only when changes affect animation behavior. For
            // on-scroll animations, this includes the element's geometry.
            // Content edits and unrelated parent option previews must not
            // replay the animation.
            const { classList, dataset, style } = this.el;
            const isAnimateOnScroll = classList.contains("o_animate_on_scroll");
            return JSON.stringify({
                animationClasses: [...classList]
                    .filter((className) => className.startsWith("o_anim_"))
                    .sort(),
                intensity: style.getPropertyValue("--wanim-intensity"),
                animationDelay: isAnimateOnScroll ? undefined : style.animationDelay,
                animationDuration: style.animationDuration,
                onScroll: isAnimateOnScroll
                    ? {
                          out: classList.contains("o_animate_out"),
                          both: classList.contains("o_animate_both_scroll"),
                          zoneStart: dataset.scrollZoneStart,
                          zoneEnd: dataset.scrollZoneEnd,
                          offsetTop: this.getElementOffsetTop(this.el),
                          offsetHeight: this.el.offsetHeight,
                      }
                    : undefined,
            });
        }
    };

registry.category("public.interactions.edit").add("website.animation", {
    Interaction: Animation,
    mixin: AnimationEdit,
});
