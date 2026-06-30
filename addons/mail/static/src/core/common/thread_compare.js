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
        const aMessageDatetime = thread1.newestPersistentOfAllMessage?.datetime;
        const bMessageDateTime = thread2.newestPersistentOfAllMessage?.datetime;
        if (!aMessageDatetime && bMessageDateTime) {
            return 1;
        }
        if (!bMessageDateTime && aMessageDatetime) {
            return -1;
        }
        if (aMessageDatetime && bMessageDateTime && aMessageDatetime !== bMessageDateTime) {
            return bMessageDateTime - aMessageDatetime;
        }
    },
    { sequence: 40 }
);
