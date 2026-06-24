import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { usePartnerAvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        this.correspondentAvatarCard = usePartnerAvatarCard();
    },
    get correspondentPartner() {
        if (this.thread?.channel?.channel_type !== "chat") {
            return undefined;
        }
        return this.thread.channel.correspondent?.partner_id;
    },
    onClickThreadAvatar(ev) {
        this.correspondentAvatarCard.open(ev, this.correspondentPartner);
    },
});
