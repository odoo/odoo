import { partnerCompareRegistry } from "@mail/core/common/partner_compare";

partnerCompareRegistry.add(
    "im_livechat.available",
    (p1, p2, { thread, u1, u2 }) => {
        if (
            u1 &&
            u2 &&
            thread?.channel?.channel_type === "livechat" &&
            u1.is_available !== u2.is_available
        ) {
            return u1.is_available ? -1 : 1;
        }
    },
    { sequence: 15 }
);

partnerCompareRegistry.add(
    "im_livechat.invite-count",
    (p1, p2, { thread, u1, u2 }) => {
        if (
            u1 &&
            u2 &&
            thread?.channel?.channel_type === "livechat" &&
            u1.invite_by_self_count !== u2.invite_by_self_count
        ) {
            return u2.invite_by_self_count - u1.invite_by_self_count;
        }
    },
    { sequence: 20 }
);
