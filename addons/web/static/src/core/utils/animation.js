import { onMounted, onWillUnmount, signal } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

/**
 * Durations of the animations shared through `animation.scss`, in milliseconds.
 * A mark has to outlast the animation it stands for, and CSS cannot tell this
 * side how long that is.
 */
export const ANIMATION_DURATION = {
    /** @see $o-mountAnimation-duration */
    mount: 200,
    /** @see o-star-fillAnimation */
    star: 450,
};

// The mark is dropped a frame or two after the animation is due, rather than on
// the dot: the animation only starts on the paint that follows the mark, so
// clearing it on time would cut its last frames and snap the element to its
// resting state.
const MARK_GRACE = 50;

/**
 * Marks what was just done, and only it, for a CSS animation to hang on.
 *
 * An animation plays whenever its element is mounted, and an element is mounted
 * again on every view change — so neither the element nor a lasting state can be
 * what carries it, or the animation replays for a click that never happened.
 *
 * The mark clears itself once the animation has had the time to play, which is
 * what keeps a mark kept outside of the element it is for — in a service, say —
 * from acknowledging the next mount.
 *
 * @param {number} duration length of the animation being marked, in ms
 * @returns {{ value: any, mark: (value?: any) => void, clear: () => void }}
 */
export function animationMark(duration) {
    const marked = signal(false);
    let timeout;
    return {
        /** What was just done, back to `false` once the animation has played. */
        get value() {
            return marked();
        },
        /**
         * @param {any} [value] what was just done, for a component animating one
         *  of several things — the star that was just clicked, out of a row of
         *  them. `true` when there is only one thing to tell apart.
         */
        mark(value = true) {
            browser.clearTimeout(timeout);
            marked.set(value);
            timeout = browser.setTimeout(() => marked.set(false), duration + MARK_GRACE);
        },
        /** Drops a pending mark, so that it cannot outlive what it stands for. */
        clear() {
            browser.clearTimeout(timeout);
        },
    };
}

/**
 * `animationMark` for a component: a pending mark dies with it.
 *
 * @see animationMark
 * @param {number} duration length of the animation being marked, in ms
 */
export function useAnimationMark(duration) {
    const animation = animationMark(duration);
    onWillUnmount(animation.clear);
    return animation;
}

/**
 * Grows an element from nothing to the height it computes to.
 *
 * Height is what a section takes as it appears in a column, and `auto` is not a
 * value CSS can animate from — so the height is measured here and the growth is
 * handed to the Web Animations API. Where the end value is known, the growth
 * belongs in a keyframe instead. @see o-mountAnimation
 *
 * @param {HTMLElement} el
 * @param {number} [duration] length of the growth, in ms
 */
export function unfoldHeight(el, duration = ANIMATION_DURATION.mount) {
    if (browser.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
    }
    // The content is laid out at its full height from the first frame, and would
    // spill out of the box while the box is still short.
    el.classList.add("overflow-hidden");
    el.animate({ height: ["0px", getComputedStyle(el).height] }, { duration, easing: "ease-out" })
        .finished.then(() => el.classList.remove("overflow-hidden"));
}

/**
 * Unfolds an element as it is mounted, but only when a mark says an interaction
 * is what brought it about: a component keyed on a record is mounted again on
 * every record moved to, and mounting alone must not animate it.
 *
 * @see unfoldHeight
 * @param {import("@odoo/owl").Signal<HTMLElement>} rootRef ref on the element
 *  that grows
 * @param {() => { value: any }} getMark reads the mark to unfold on, held
 *  wherever the interaction happens
 */
export function useUnfoldOnMount(rootRef, getMark) {
    onMounted(() => {
        const el = rootRef();
        if (el && getMark()?.value) {
            unfoldHeight(el);
        }
    });
}
