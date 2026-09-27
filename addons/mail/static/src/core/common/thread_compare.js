import { compareDatetime } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";

/**
 * Registry of functions to sort threads in messaging menu.
 * The expected value is a function with the following
 * signature:
 *     (thread1: Thread, thread2: Thread) => number | undefined
 */
export const threadCompareRegistry = registry.category("mail.thread_compare");

/**
 * Runs the registered comparators in sequence, the first one having an opinion decides.
 *
 * @param {import("models").Thread} thread1
 * @param {import("models").Thread} thread2
 */
export function compareThreads(thread1, thread2) {
    for (const fn of threadCompareRegistry.getAll()) {
        const result = fn(thread1, thread2);
        if (result !== undefined) {
            return result;
        }
    }
    return 0;
}

threadCompareRegistry.add(
    "mail.message-datetime",
    /**
     * @param {import("models").Thread thread1}
     * @param {import("models").Thread thread2}
     */
    (thread1, thread2) => {
        const aMessageDatetime = thread1.newestPersistentOfAllMessage?.datetime;
        const bMessageDateTime = thread2.newestPersistentOfAllMessage?.datetime;
        if (!aMessageDatetime && bMessageDateTime) {
            return 1;
        }
        if (!bMessageDateTime && aMessageDatetime) {
            return -1;
        }
        if (aMessageDatetime && bMessageDateTime) {
            const res = compareDatetime(bMessageDateTime, aMessageDatetime);
            if (res !== 0) {
                return res;
            }
        }
        const aCreate = thread1.channel?.create_date;
        const bCreate = thread2.channel?.create_date;
        if (aCreate && bCreate) {
            const res = compareDatetime(bCreate, aCreate);
            if (res !== 0) {
                return res;
            }
        }
    },
    { sequence: 40 }
);
