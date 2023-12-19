/** @odoo-module alias=@mail/../tests/helpers/time_control default=false */

import { browser } from "@web/core/browser/browser";
import { uniqueId } from "@web/core/utils/functions";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

/**
 * Wait a task tick, so that anything in micro-task queue that can be processed
 * is processed.
 */
async function nextTick() {
    await new Promise(setTimeout);
}

export function getAdvanceTime() {
    // list of timeout ids that have timed out.
    let timedOutIds = [];
    // key: timeoutId, value: func + remaining duration
    const timeouts = new Map();
    patchWithCleanup(browser, {
        clearTimeout: (id) => {
            timeouts.delete(id);
            timedOutIds = timedOutIds.filter((i) => i !== id);
        },
        setTimeout: (func, duration) => {
            const timeoutId = uniqueId("timeout_");
            const timeout = {
                id: timeoutId,
                isTimedOut: false,
                func,
                duration,
            };
            timeouts.set(timeoutId, timeout);
            if (duration === 0) {
                timedOutIds.push(timeoutId);
                timeout.isTimedOut = true;
            }
            return timeoutId;
        },
    });
    return async function (duration) {
        await nextTick();
        for (const id of timeouts.keys()) {
            const timeout = timeouts.get(id);
            if (timeout.isTimedOut) {
                continue;
            }
            timeout.duration = Math.max(timeout.duration - duration, 0);
            if (timeout.duration === 0) {
                timedOutIds.push(id);
            }
        }
        while (timedOutIds.length > 0) {
            const id = timedOutIds.shift();
            const timeout = timeouts.get(id);
            timeouts.delete(id);
            timeout.func();
            await nextTick();
        }
    };
}
