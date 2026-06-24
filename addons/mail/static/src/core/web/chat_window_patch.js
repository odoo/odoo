import { ChatWindow } from "@mail/core/common/chat_window";
import { usePartnerAvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { patch } from "@web/core/utils/patch";

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.correspondentAvatarCard = usePartnerAvatarCard({
            stopPropagation: true,
        });
    },
    get correspondentPartner() {
        if (this.channel?.channel_type !== "chat") {
            return undefined;
        }
        return this.channel.correspondent?.partner_id;
    },
    onClickThreadAvatar(ev) {
        this.correspondentAvatarCard.open(ev, this.correspondentPartner);
    },
});
