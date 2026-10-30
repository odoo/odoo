import { PartnerSuggestionPlugin } from "@mail/core/common/plugin/suggestion/partner_suggestion_plugin";

import { patch } from "@web/core/utils/patch";

patch(PartnerSuggestionPlugin.prototype, {
    /** @override */
    getPartners() {
        const thread = this.deps.getThread();
        const isNonPublicChannel =
            thread &&
            (thread.channel?.channel_type === "group" ||
                thread.channel?.channel_type === "chat" ||
                (thread.channel?.channel_type === "channel" &&
                    (thread.channel.parent_channel_id || thread).group_public_id));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            const partnersById = new Map(
                [
                    ...(thread.channel?.channel_member_ids ?? []),
                    ...(thread.channel?.parent_channel_id?.channel_member_ids ?? []),
                ]
                    .filter((m) => m.partner_id)
                    .map((m) => [m.partner_id.id, m.partner_id])
            );
            if (thread.channel?.channel_type === "channel") {
                const group = (thread.channel.parent_channel_id || thread).group_public_id;
                group.partners.forEach((partner) => partnersById.set(partner.id, partner));
            }
            return Array.from(partnersById.values());
        } else {
            return super.getPartners();
        }
    },
    /** @override */
    isPartnerValid(partner) {
        if (this.deps.getThread()?.channel && partner.eq(this.store.odoobot)) {
            return true;
        }
        return super.isPartnerValid(partner);
    },
});
