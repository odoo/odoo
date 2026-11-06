import { PartnerSuggestionPlugin } from "@mail/core/common/plugin/suggestion/partner_suggestion_plugin";

import { patch } from "@web/core/utils/patch";

patch(PartnerSuggestionPlugin.prototype, {
    /** @override */
    getPartners() {
        const channel = this.deps.getThread()?.channel;
        const allowedGroup = (channel?.parent_channel_id ?? channel)?.group_public_id;
        const isNonPublicChannel =
            channel?.channel_type === "group" ||
            channel?.channel_type === "chat" ||
            (channel?.channel_type === "channel" && allowedGroup);
        if (!isNonPublicChannel) {
            return super.getPartners();
        }
        // Only suggest partners who can read the conversation: a mention notifies the
        // mentioned partner, which would leak the message to anyone else.
        const partnersById = new Map(
            [
                ...channel.channel_member_ids,
                ...(channel.parent_channel_id?.channel_member_ids ?? []),
            ]
                .filter((m) => m.partner_id)
                .map((m) => [m.partner_id.id, m.partner_id])
        );
        if (channel.channel_type === "channel") {
            allowedGroup.partners.forEach((partner) => partnersById.set(partner.id, partner));
        }
        return [...partnersById.values()].filter((partner) => this.isPartnerValid(partner));
    },
    /** @override */
    isPartnerValid(partner) {
        if (this.deps.getThread()?.channel && partner.eq(this.store.odoobot)) {
            return true;
        }
        return super.isPartnerValid(partner);
    },
});
