import { Animation } from "./animation";
import { registry } from "@web/core/registry";

const ANIM_EFFECT_CLASSES = [
    "o_anim_fade_in",
    "o_anim_slide_in",
    "o_anim_bounce_in",
    "o_anim_rotate_in",
    "o_anim_zoom_out",
    "o_anim_zoom_in",
    "o_anim_flash",
    "o_anim_pulse",
    "o_anim_shake",
    "o_anim_tada",
    "o_anim_flip_in_x",
    "o_anim_flip_in_y",
];

const ANIM_DIRECTION_CLASSES = [
    "o_anim_from_right",
    "o_anim_from_left",
    "o_anim_from_bottom",
    "o_anim_from_top",
    "o_anim_from_top_right",
    "o_anim_from_top_left",
    "o_anim_from_bottom_right",
    "o_anim_from_bottom_left",
];

const AnimationEdit = I => class extends I {
    destroy() {
        // We remove the "o_animate_preview" class here because it is added when
        // an animation is selected in the options, and the "Animation"
        // interaction considers it as part of the initial state. We remove it
        // here because otherwise it is added back when exiting edit mode.
        this.el.classList.remove("o_animate_preview");
    }

    getConfigurationSnapshot() {
        const { classList, dataset, style } = this.el;
        const isAnimateOnScroll = classList.contains("o_animate_on_scroll");
        return JSON.stringify({
            isAnimateOnScroll,
            isAnimateOnScrollOut: classList.contains("o_animate_out"),
            isAnimateBothScroll: classList.contains("o_animate_both_scroll"),
            effect: ANIM_EFFECT_CLASSES.find((className) => classList.contains(className)),
            direction: ANIM_DIRECTION_CLASSES.find((className) => classList.contains(className)),
            intensity: style.getPropertyValue("--wanim-intensity"),
            animationDelay: isAnimateOnScroll ? undefined : style.animationDelay,
            animationDuration: style.animationDuration,
            scrollZoneStart: isAnimateOnScroll ? dataset.scrollZoneStart : undefined,
            scrollZoneEnd: isAnimateOnScroll ? dataset.scrollZoneEnd : undefined,
        });
    }
};

registry
    .category("public.interactions.edit")
    .add("website.animation", {
        Interaction: Animation,
        mixin: AnimationEdit,
    });
