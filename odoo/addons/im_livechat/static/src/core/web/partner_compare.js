/* @odoo-module */

import { partnerCompareRegistry } from "@mail/core/common/partner_compare";

partnerCompareRegistry.add(
    "im_livechat.available",
    (p1, p2, { thread }) => {
        if (thread?.type === "livechat" && p1.is_available !== p2.is_available) {
            return p1.is_available ? -1 : 1;
        }
    },
    { sequence: 15 }
);

partnerCompareRegistry.add(
    "im_livechat.invite-count",
    (p1, p2, { thread }) => {
        if (thread?.type === "livechat" && p1.invite_by_self_count !== p2.invite_by_self_count) {
            return p2.invite_by_self_count - p1.invite_by_self_count;
        }
    },
    { sequence: 20 }
);
