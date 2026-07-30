import { compareDatetime } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";

/**
 * Registry of functions to sort threads in messaging menu.
 * The expected value is a function with the following
 * signature:
 *     (thread1: Thread, thread2: Thread) => number | undefined
 */
export const threadCompareRegistry = registry.category("mail.thread_compare");

threadCompareRegistry.add(
    "mail.message-datetime",
    /**
     * @param {import("models").Thread thread1}
     * @param {import("models").Thread thread2}
     */
    (thread1, thread2) => {
        const aTime =
            thread1.newestPersistentOfAllMessage?.datetime ?? thread1.channel?.create_date;
        const bTime =
            thread2.newestPersistentOfAllMessage?.datetime ?? thread2.channel?.create_date;
        if (!aTime && bTime) {
            return 1;
        }
        if (!bTime && aTime) {
            return -1;
        }
        if (aTime && bTime) {
            const res = compareDatetime(bTime, aTime);
            if (res !== 0) {
                return res;
            }
        }
    },
    { sequence: 40 }
);
