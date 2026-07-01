import { threadCompareRegistry } from "@mail/core/common/thread_compare";

threadCompareRegistry.add(
    "im_livechat.self_chats_first",
    (t1, t2) => {
        if (t1.channel?.channel_type !== "livechat" && t2.channel?.channel_type !== "livechat") {
            return;
        }
        const c1Mine = Boolean(t1.channel.self_member_id?.isSelf);
        const c2Mine = Boolean(t2.channel.self_member_id?.isSelf);
        if (c2Mine && !c1Mine) {
            return 1;
        }
        if (c1Mine && !c2Mine) {
            return -1;
        }
    },
    { sequence: 30 }
);
