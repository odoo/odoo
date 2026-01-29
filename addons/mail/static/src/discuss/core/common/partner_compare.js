/* @odoo-module */

import { partnerCompareRegistry } from "@mail/core/common/partner_compare";

partnerCompareRegistry.add(
    "discuss.recent-chats",
    (p1, p2, { env, context }) => {
        const recentChatPartnerIds =
            context.recentChatPartnerIds || env.services["mail.persona"].getRecentChatPartnerIds();
        const recentChatIndex_p1 = recentChatPartnerIds.findIndex(
            (partnerId) => partnerId === p1.id
        );
        const recentChatIndex_p2 = recentChatPartnerIds.findIndex(
            (partnerId) => partnerId === p2.id
        );
        if (recentChatIndex_p1 !== -1 && recentChatIndex_p2 === -1) {
            return -1;
        } else if (recentChatIndex_p1 === -1 && recentChatIndex_p2 !== -1) {
            return 1;
        } else if (recentChatIndex_p1 < recentChatIndex_p2) {
            return -1;
        } else if (recentChatIndex_p1 > recentChatIndex_p2) {
            return 1;
        }
    },
    { sequence: 25 }
);

partnerCompareRegistry.add(
    "discuss.members",
    (p1, p2, { thread, memberPartnerIds }) => {
        if (thread?.model === "discuss.channel") {
            const isMember1 = memberPartnerIds.has(p1.id);
            const isMember2 = memberPartnerIds.has(p2.id);
            if (isMember1 && !isMember2) {
                return -1;
            }
            if (!isMember1 && isMember2) {
                return 1;
            }
        }
    },
    { sequence: 40 }
);
