import { Thread } from "@mail/core/common/thread";
import { usePartnerAvatarCardOnClick } from "@mail/core/web/avatar_card/avatar_card";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        usePartnerAvatarCardOnClick(this.startMessageAvatarRef, () =>
            this.channel?.hasCorrespondentAvatar ? this.channel.correspondentPartner : undefined
        );
    },
    get startMessageAvatarAttClass() {
        return {
            ...super.startMessageAvatarAttClass,
            "cursor-pointer":
                this.channel?.hasCorrespondentAvatar && this.channel.correspondentPartner,
        };
    },
});
