import { threadCompareRegistry } from "@mail/core/common/thread_compare";
import { compareDatetime } from "@mail/utils/common/misc";

threadCompareRegistry.add(
    "mail.favorite",
    (t1, t2) => {
        const c1Fav = Boolean(t1.channel?.self_member_id?.is_favorite);
        const c2Fav = Boolean(t2.channel?.self_member_id?.is_favorite);
        if (c2Fav && !c1Fav) {
            return 1;
        }
        if (c1Fav && !c2Fav) {
            return -1;
        }
    },
    { sequence: 10 }
);

threadCompareRegistry.add(
    "mail.last-interest",
    /**
     * @param {import("models").Thread thread1}
     * @param {import("models").Thread thread2}
     */
    (thread1, thread2) => {
        const aLastInterestDt = thread1.channel?.lastInterestDt;
        const bLastInterestDt = thread2.channel?.lastInterestDt;
        if (aLastInterestDt && bLastInterestDt) {
            const res = compareDatetime(bLastInterestDt, aLastInterestDt);
            if (res !== 0) {
                return res;
            }
        }
    },
    { sequence: 60 }
);
