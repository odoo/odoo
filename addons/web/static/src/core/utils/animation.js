import { onPatched, signal } from "@odoo/owl";

/**
 * Marks what was just done, for a CSS animation to hang on. The mark clears
 * once the animations under `ref` have finished.
 *
 * @returns {{ ref: () => HTMLElement | null, value: () => any, mark: (value?: any) => void }}
 */
export function useAnimationMark() {
    const ref = signal.ref();
    const marked = signal(false);
    let isPending = false;
    let generation = 0;
    onPatched(() => {
        if (!isPending) {
            return;
        }
        isPending = false;
        const current = ++generation;
        const animations = ref()?.getAnimations({ subtree: true }) ?? [];
        Promise.allSettled(animations.map((animation) => animation.finished)).then(() => {
            if (current === generation) {
                marked.set(false);
            }
        });
    });
    return {
        ref,
        /** What was just done, `false` once its animations have played. */
        value() {
            return marked();
        },
        /**
         * @param {any} [value] what was just done, for a component animating one
         *  of several things (the star that was just clicked, out of a row of
         *  them). `true` when there is only one thing to tell apart.
         */
        mark(value = true) {
            marked.set(value);
            isPending = true;
        },
    };
}
