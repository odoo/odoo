import {
    GEOMETRY_ANIMATION_DURATION,
    GEOMETRY_ANIMATION_EASING,
    GeometryRenderer,
} from "@mail/discuss/call/common/meeting_geometry_renderer";

import { describe, expect, test } from "@odoo/hoot";

/**
 * Phases 3-4 acceptance: geometry changes are handed to the Web Animations API as a `transform`
 * animation (compositor-only, outside the OWL render loop) instead of jumping. New surfaces snap,
 * equal targets are no-ops, and a new target interrupts the running animation from the current
 * visual (latest-layout-wins): only the current visual and the latest target are ever kept, never
 * a queued animation.
 *
 * The interpolation itself belongs to the browser, so what is asserted here is what the renderer
 * hands over: the resting geometry written inline, the keyframes of the animation that overrides
 * it, and that the previous animation was cancelled rather than queued. Animations are driven
 * through {@link fakeEl}'s stub so a mid-flight interruption can be exercised at an exact point.
 */

describe.current.tags("desktop");

const DURATION = GEOMETRY_ANIMATION_DURATION;

/**
 * A minimal stand-in for an HTMLElement whose animations can be driven explicitly.
 *
 * @returns {{style: Object, animations: Object[], animate: Function}}
 */
function fakeEl() {
    const el = {
        style: {},
        animations: [],
        animate(keyframes, options) {
            const animation = {
                keyframes,
                options,
                // A just-created animation has not started yet: it has no progress of its own.
                playState: "running",
                progress: null,
                effect: { getComputedTiming: () => ({ progress: animation.progress }) },
                cancel() {
                    animation.playState = "idle";
                },
                /** @param {number} progress 0 → 1 */
                seek(progress) {
                    if (progress >= 1) {
                        animation.progress = null;
                        animation.playState = "finished";
                        return;
                    }
                    animation.progress = progress;
                },
            };
            el.animations.push(animation);
            return animation;
        },
    };
    return el;
}

/** @returns {Object|undefined} the last animation started on `el`. */
function lastAnimation(el) {
    return el.animations.at(-1);
}

/** @returns {string[]} the `transform` of every keyframe of the last animation started on `el`. */
function lastKeyframes(el) {
    return lastAnimation(el).keyframes.map((keyframe) => keyframe.transform);
}

describe("meeting geometry renderer", () => {
    test("a new surface snaps to its target without animating", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 10, y: 20, width: 300, height: 200 }, el);
        expect(el.style.width).toBe("300px");
        expect(el.style.height).toBe("200px");
        expect(el.style.transform).toBe("translate3d(10px, 20px, 0)");
        expect(el.animations).toHaveLength(0);
    });

    test("re-applying the same target is a no-op", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        const rect = { x: 10, y: 20, width: 300, height: 200 };
        renderer.setTarget("a", rect, el);
        renderer.setTarget("a", { ...rect }, el);
        expect(el.style.transform).toBe("translate3d(10px, 20px, 0)");
        expect(el.animations).toHaveLength(0);
    });

    test("a move is handed over as a transform animation over the resting geometry", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 50, width: 200, height: 200 }, el);
        // The box is already the target size and the inline transform already rests on the target:
        // the animation only overrides it while it runs, scaling the box back to the old size.
        expect(el.style.width).toBe("200px");
        expect(el.style.height).toBe("200px");
        expect(el.style.transform).toBe("translate3d(100px, 50px, 0)");
        expect(lastKeyframes(el)).toEqual([
            "translate3d(0px, 0px, 0) scale(0.5, 0.5)",
            "translate3d(100px, 50px, 0) scale(1, 1)",
        ]);
        expect(lastAnimation(el).options).toEqual({
            duration: DURATION,
            easing: GEOMETRY_ANIMATION_EASING,
        });
    });

    test("a new target interrupts the running animation from the current visual", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 50, width: 200, height: 200 }, el);
        const interrupted = lastAnimation(el);
        interrupted.seek(0.5); // visual is (50, 25, 150, 150)
        expect(renderer.currentRect("a")).toEqual({ x: 50, y: 25, width: 150, height: 150 });

        renderer.setTarget("a", { x: 200, y: 100, width: 300, height: 300 }, el);
        expect(interrupted.playState).toBe("idle");
        expect(lastKeyframes(el)).toEqual([
            "translate3d(50px, 25px, 0) scale(0.5, 0.5)",
            "translate3d(200px, 100px, 0) scale(1, 1)",
        ]);
        expect(el.style.transform).toBe("translate3d(200px, 100px, 0)");
    });

    test("targets set before any frame only animate to the latest one", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        // Two changes in the same frame: B must never be rendered, only C. The B animation has not
        // started, so the surface is still visually at A.
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        const skipped = lastAnimation(el);
        renderer.setTarget("a", { x: 0, y: 200, width: 100, height: 100 }, el);
        expect(skipped.playState).toBe("idle");
        expect(lastKeyframes(el)).toEqual([
            "translate3d(0px, 0px, 0) scale(1, 1)",
            "translate3d(0px, 200px, 0) scale(1, 1)",
        ]);
    });

    test("rapid A -> B -> C -> D never queues: only the current visual and the latest target are kept", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        lastAnimation(el).seek(0.5); // mid A -> B: visual (50, 0, 100, 100)
        renderer.setTarget("a", { x: 0, y: 100, width: 100, height: 100 }, el);
        lastAnimation(el).seek(0.5); // mid -> C: visual (25, 50, 100, 100)
        expect(renderer.currentRect("a")).toEqual({ x: 25, y: 50, width: 100, height: 100 });

        renderer.setTarget("a", { x: 100, y: 100, width: 100, height: 100 }, el);
        // The final state is D; B and C were never executed as queued animations.
        expect(el.style.transform).toBe("translate3d(100px, 100px, 0)");
        expect(lastKeyframes(el)[0]).toBe("translate3d(25px, 50px, 0) scale(1, 1)");
        // A single entry per surface, and a single live animation: no queue exists.
        expect(renderer.size).toBe(1);
        expect(el.animations.filter((animation) => animation.playState === "running")).toHaveLength(
            1
        );
    });

    test("a target reverted before any frame settles without a pointless animation", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        const reverted = lastAnimation(el);
        // Revert before any frame: the visual never moved, so there is nothing to animate.
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        expect(reverted.playState).toBe("idle");
        expect(el.style.transform).toBe("translate3d(0px, 0px, 0)");
        expect(el.animations).toHaveLength(1);
    });

    test("a fresh element for an existing surface carries on from the current visual", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el1 = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el1);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el1);
        const moved = lastAnimation(el1);
        moved.seek(0.5); // visual is (50, 0, 100, 100)

        const el2 = fakeEl();
        renderer.setTarget("a", { x: 50, y: 50, width: 200, height: 100 }, el2);
        // The animation left the unmounted element and resumed on the fresh one, from the same
        // visual, so the surface never flashes at another position.
        expect(moved.playState).toBe("idle");
        expect(el2.style.width).toBe("200px");
        expect(el2.style.transform).toBe("translate3d(50px, 50px, 0)");
        expect(lastKeyframes(el2)).toEqual([
            "translate3d(50px, 0px, 0) scale(0.5, 1)",
            "translate3d(50px, 50px, 0) scale(1, 1)",
        ]);
    });

    test("a fresh element arriving while a target is pending keeps the current visual", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el1 = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el1);
        // B is set but no frame ran yet: the surface is still visually at A.
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el1);
        const el2 = fakeEl();
        // The fresh element must animate from the current visual (A), never flash B.
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el2);
        expect(lastKeyframes(el2)).toEqual([
            "translate3d(0px, 0px, 0) scale(1, 1)",
            "translate3d(100px, 0px, 0) scale(1, 1)",
        ]);
    });

    test("a non-animated target lands at once and cancels the running animation", async () => {
        // Pointer-driven geometry (dragging the inset): the surface has to be where the pointer is
        // on this very frame, and a 200ms transition would make it trail behind every step.
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        const interrupted = lastAnimation(el);
        interrupted.seek(0.5);

        renderer.setTarget("a", { x: 120, y: 40, width: 100, height: 100 }, el, { animate: false });
        expect(interrupted.playState).toBe("idle");
        expect(el.style.transform).toBe("translate3d(120px, 40px, 0)");
        expect(el.animations).toHaveLength(1);
        // The dragged position becomes the resting one, so the next layout animates out of it.
        expect(renderer.currentRect("a")).toEqual({ x: 120, y: 40, width: 100, height: 100 });
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        expect(lastKeyframes(el)[0]).toBe("translate3d(120px, 40px, 0) scale(1, 1)");
    });

    test("remove releases the element styling and cancels its animation", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        const moving = lastAnimation(el);
        renderer.remove("a", el);
        expect(moving.playState).toBe("idle");
        expect(el.style.transform).toBe("");
        expect(el.style.width).toBe("");
        expect(el.style.height).toBe("");
        expect(renderer.size).toBe(0);
    });

    test("a surface removed and re-added snaps again (no stale animation)", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        renderer.remove("a", el);
        renderer.setTarget("a", { x: 500, y: 500, width: 50, height: 50 }, el);
        expect(el.style.transform).toBe("translate3d(500px, 500px, 0)");
        expect(el.animations.filter((animation) => animation.playState === "running")).toHaveLength(
            0
        );
    });

    test("prune drops the entries of disappeared surfaces and cancels their animation", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const elA = fakeEl();
        const elB = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, elA);
        renderer.setTarget("b", { x: 100, y: 0, width: 100, height: 100 }, elB);
        renderer.setTarget("b", { x: 200, y: 0, width: 100, height: 100 }, elB);
        const pruned = lastAnimation(elB);
        renderer.prune(new Set(["a"]));
        expect(renderer.size).toBe(1);
        expect(pruned.playState).toBe("idle");
        expect(elA.style.transform).toBe("translate3d(0px, 0px, 0)");
    });

    test("dispose stops all animations", async () => {
        const renderer = new GeometryRenderer({ duration: DURATION });
        const el = fakeEl();
        renderer.setTarget("a", { x: 0, y: 0, width: 100, height: 100 }, el);
        renderer.setTarget("a", { x: 100, y: 0, width: 100, height: 100 }, el);
        const moving = lastAnimation(el);
        renderer.dispose();
        expect(moving.playState).toBe("idle");
        expect(renderer.size).toBe(0);
    });
});
