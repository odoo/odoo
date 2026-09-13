/** @odoo-module native */
import { onMounted, onWillUnmount } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
const log = makeLogger("pos.press");

/**
 * @param {Ref} ref
 * @param {Array<Object>} ranges
 * @param {number} [ranges[].delay=0]
 * @param {number} [ranges[].maxDelay]
 * @param {Function} ranges[].callback
 * @param {string} [ranges[].type="release"]
 */
export function useTimedPress(ref, ranges = []) {
    let timerStart = null;
    let pointerId = null;
    let holdTimers = [];

    const handlePointerDown = (event) => {
        if (event.button !== 0 || pointerId !== null) {
            return;
        }
        timerStart = performance.now();
        pointerId = event.pointerId;

        for (const { delay = 0, type = "release", callback } of ranges) {
            if (type === "hold" && typeof callback === "function") {
                const timer = setTimeout(() => {
                    log.logic("hold fired", () => ({ delay }));
                    callback(event, delay);
                }, delay);
                holdTimers.push(timer);
            }
        }
    };

    const handlePointerUp = (event) => {
        if (timerStart === null || event.pointerId !== pointerId) {
            return;
        }

        const elapsed = performance.now() - timerStart;
        timerStart = null;
        pointerId = null;
        clearAllHoldTimers();

        const fired = [];
        for (const { delay = 0, maxDelay, type = "release", callback } of ranges) {
            if (type === "release" && typeof callback === "function") {
                if (
                    elapsed >= delay &&
                    (maxDelay === undefined || elapsed < maxDelay)
                ) {
                    fired.push(delay);
                    callback(event, elapsed);
                }
            }
        }
        log.logic("pointerup", () => ({
            elapsed: Number(elapsed.toFixed(1)),
            releaseFired: fired,
        }));
    };

    const cancel = (event) => {
        if (event && event.pointerId !== pointerId) {
            return;
        }
        log.lifecycle("press canceled", () => ({
            pointerId,
            timers: holdTimers.length,
        }));
        timerStart = null;
        pointerId = null;
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
        cancel();
        const el = ref.el;
        el?.removeEventListener("pointerdown", handlePointerDown);
        el?.removeEventListener("pointerup", handlePointerUp);
        el?.removeEventListener("pointerleave", cancel);
        el?.removeEventListener("pointercancel", cancel);
    });
}
