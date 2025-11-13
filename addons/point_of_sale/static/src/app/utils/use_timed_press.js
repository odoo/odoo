import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * `useTimedPress` — A hook to detect and respond to different press durations on a DOM element.
 *
 * It supports two types of interactions:
 * - `"release"` (default): Triggers the callback **after the pointer is released**, if the duration falls within the defined delay range.
 * - `"hold"`: Triggers the callback after a given delay **while the pointer is held down**.
 *
 * This hook is compatible with mouse, touch, and stylus inputs via `pointer` events.
 *
 * @param {Ref} ref - An OWL `useRef` pointing to the target DOM element.
 * @param {Array<Object>} ranges - An array of press range objects defining when and how to trigger callbacks.
 *   Each object supports the following properties:
 *   @param {number} [ranges[].delay=0] - Minimum duration in milliseconds before the callback can be triggered.
 *   @param {number} [ranges[].maxDelay] - Optional maximum duration; if specified, the callback is only triggered if the press duration is less than this value.
 *   @param {Function} ranges[].callback - The function to execute. It receives the original pointer event and the press duration in milliseconds (for `"release"`).
 *     Signature: `(event: PointerEvent, duration: number) => void`
 *   @param {string} [ranges[].type="release"] - Determines when to trigger the callback:
 *     - `"hold"`: triggers while holding the press after `delay`
 *     - `"release"`: triggers after release if the press duration is within `[delay, maxDelay)`
 *
 * @example
 * useTimedPress(myRef, [
 *   {
 *     delay: 600,
 *     callback: (e, duration) => console.log("Long press while holding"),
 *     type: "hold",
 *   },
 *   {
 *     delay: 0,
 *     maxDelay: 200,
 *     callback: (e, duration) => console.log("Tap released", duration),
 *     type: "release",
 *   },
 *   {
 *     delay: 600,
 *     callback: (e, duration) => console.log("Long press released", duration),
 *     type: "release",
 *   },
 * ]);
 */
export function useTimedPress(ref, ranges = []) {
    let timerStart = null;
    let holdTimers = [];

    const handlePointerDown = (event) => {
        if (event.button !== 0) {
            return;
        }
        timerStart = performance.now();

        for (const { delay = 0, type = "release", callback } of ranges) {
            if (type === "hold" && typeof callback === "function") {
                const timer = setTimeout(() => {
                    callback(event, delay);
                }, delay);
                holdTimers.push(timer);
            }
        }
    };

    const handlePointerUp = (event) => {
        if (timerStart === null) {
            return;
        }

        const elapsed = performance.now() - timerStart;
        timerStart = null;
        clearAllHoldTimers();

        for (const { delay = 0, maxDelay, type = "release", callback } of ranges) {
            if (type === "release" && typeof callback === "function") {
                if (elapsed >= delay && (maxDelay === undefined || elapsed < maxDelay)) {
                    callback(event, elapsed);
                }
            }
        }
    };

    const cancel = () => {
        timerStart = null;
        clearAllHoldTimers();
    };

    const clearAllHoldTimers = () => {
        for (const timer of holdTimers) {
            clearTimeout(timer);
        }
        holdTimers = [];
    };

    onMounted(() => {
        const el = ref.el;
        el?.addEventListener("pointerdown", handlePointerDown);
        el?.addEventListener("pointerup", handlePointerUp);
        el?.addEventListener("pointerleave", cancel);
        el?.addEventListener("pointercancel", cancel);
    });

    onWillUnmount(() => {
        const el = ref.el;
        el?.removeEventListener("pointerdown", handlePointerDown);
        el?.removeEventListener("pointerup", handlePointerUp);
        el?.removeEventListener("pointerleave", cancel);
        el?.removeEventListener("pointercancel", cancel);
    });
}
