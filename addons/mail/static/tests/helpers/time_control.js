/** @odoo-module **/

import { nextTick } from '@mail/utils/utils';

import { browser } from '@web/core/browser/browser';
import { patchWithCleanup } from "@web/../tests/helpers/utils";

export function getAdvanceTime() {
    // list of timeout ids that have timed out.
    let timedOutIds = [];
    // key: timeoutId, value: func + remaining duration
    const timeouts = new Map();
    patchWithCleanup(browser, {
        clearTimeout: id => {
            timeouts.delete(id);
            timedOutIds = timedOutIds.filter(i => i !== id);
        },
        setTimeout: (func, duration) => {
            const timeoutId = _.uniqueId('timeout_');
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
