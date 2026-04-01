import { threadCompareRegistry } from "@mail/core/common/thread_compare";
import { compareDatetime } from "@mail/utils/common/misc";

threadCompareRegistry.add(
    "mail.unread",
    /**
     * @param {import("models").Thread thread1}
     * @param {import("models").Thread thread2}
     */
    (thread1, thread2) => {
        const aUnread = thread1.self_member_id?.message_unread_counter;
        const bUnread = thread2.self_member_id?.message_unread_counter;
        if (aUnread > 0 && bUnread === 0) {
            return -1;
        }
        if (bUnread > 0 && aUnread === 0) {
            return 1;
        }
    },
    { sequence: 20 }
);

threadCompareRegistry.add(
    "mail.last-interest",
    /**
     * @param {import("models").Thread thread1}
     * @param {import("models").Thread thread2}
     */
    (thread1, thread2) => {
        const aLastInterestDt = thread1.lastInterestDt;
        const bLastInterestDt = thread2.lastInterestDt;
        if (aLastInterestDt && bLastInterestDt) {
            const res = compareDatetime(bLastInterestDt, aLastInterestDt);
            if (res !== 0) {
                return res;
            }
        }
    },
    { sequence: 30 }
);
