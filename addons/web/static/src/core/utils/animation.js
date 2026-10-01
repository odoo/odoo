import { onWillUnmount, signal } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

/**
 * Durations of the animations shared through `animation.scss`, in milliseconds.
 * A mark has to outlast the animation it stands for, and CSS cannot tell this
 * side how long that is.
 */
export const ANIMATION_DURATION = {
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
 * The mark clears itself once the animation has had the time to play, and a
 * pending one dies with the component that made it.
 *
 * @param {number} duration length of the animation being marked, in ms
 * @returns {{ value: () => any, mark: (value?: any) => void }}
 */
export function useAnimationMark(duration) {
    const marked = signal(false);
    let timeout;
    onWillUnmount(() => browser.clearTimeout(timeout));
    return {
        /** What was just done, back to `false` once the animation has played. */
        value() {
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
    };
}
