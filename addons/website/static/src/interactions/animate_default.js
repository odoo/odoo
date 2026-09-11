import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import {
    applyDefaultAnimationClass,
    DEFAULT_ANIMATION_CLASS,
} from "@website/utils/animate_default";

/**
 * Marks the blocks the "Animation" theme option animates (see
 * "@website/utils/animate_default").
 *
 * Must run before "AnimateDefaultReveal", which matches on that very class:
 * interactions are started in registry order, hence the sequence below.
 */
export class AnimateDefault extends Interaction {
    static selector = "#wrapwrap";

    setup() {
        applyDefaultAnimationClass(this.el);
    }
}

/**
 * Plays the theme's default animation once, when its block comes into view.
 *
 * Not the "Animation" interaction on purpose: the theme's animation is not
 * configurable, as any option converts the block to a regular "o_animate" one
 * that interaction then handles. A reveal is all that is left, and an observer
 * does it without a scroll listener per block - and without the page-wide
 * "resize" that interaction dispatches whenever an animation ends.
 *
 * The CSS keeps the animation paused until "o_animating" is set below, so there
 * is nothing to rewind here.
 */
export class AnimateDefaultReveal extends Interaction {
    static selector = `.${DEFAULT_ANIMATION_CLASS}`;
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                o_animating: this.isAnimating,
                o_animated: this.isAnimated,
            }),
            "t-on-animationend": this.onAnimationEnd,
        },
    };

    setup() {
        this.isAnimating = false;
        this.isAnimated = false;
    }

    start() {
        // No margin or threshold: anything they would shrink the viewport by
        // is a band a block can sit in entirely, at the bottom of a page that
        // does not scroll, and never be revealed in.
        const observer = new IntersectionObserver((entries) => {
            if (entries.some((entry) => entry.isIntersecting)) {
                observer.disconnect();
                this.reveal();
            }
        });
        observer.observe(this.el);
        this.registerCleanup(() => observer.disconnect());
    }

    reveal() {
        this.isAnimating = true;
        this.updateContent();
    }

    onAnimationEnd(ev) {
        // "animationend" bubbles: an animation of the content is not this one.
        if (ev.target !== this.el) {
            return;
        }
        this.isAnimating = false;
        this.isAnimated = true;
        this.updateContent();
    }

    /**
     * "AnimateOverflow" clamps the overflow of the page while a block animates,
     * and listens for this.
     */
    updateContent() {
        super.updateContent();
        this.el.dispatchEvent(new Event("updatecontent", { bubbles: true }));
    }
}

registry
    .category("public.interactions")
    .add("website.animate_default", AnimateDefault, { sequence: 10 });
registry
    .category("public.interactions")
    .add("website.animate_default_reveal", AnimateDefaultReveal);

registry
    .category("public.interactions.edit")
    .add("website.animate_default", { Interaction: AnimateDefault }, { sequence: 10 });
registry
    .category("public.interactions.edit")
    .add("website.animate_default_reveal", { Interaction: AnimateDefaultReveal });
