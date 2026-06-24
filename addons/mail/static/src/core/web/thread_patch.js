import { Thread } from "@mail/core/common/thread";
import { usePartnerAvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.startMessageAvatarCard = usePartnerAvatarCard();
    },
    get startMessageAvatarPartner() {
        if (this.channel?.channel_type !== "chat") {
            return undefined;
        }
        return this.channel.correspondent?.partner_id;
    },
    onClickStartMessageAvatar(ev) {
        this.startMessageAvatarCard.open(ev, this.startMessageAvatarPartner);
    },
});
