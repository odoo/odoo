import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { usePartnerAvatarCardOnClick } from "@mail/core/web/avatar_card/avatar_card";

import { patch } from "@web/core/utils/patch";

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        usePartnerAvatarCardOnClick(this.threadAvatarRef, () =>
            this.thread?.channel?.hasCorrespondentAvatar
                ? this.thread.channel.correspondentPartner
                : undefined
        );
    },
    get threadAvatarAttClass() {
        return {
            ...super.threadAvatarAttClass,
            "cursor-pointer":
                this.thread?.channel?.hasCorrespondentAvatar &&
                this.thread.channel.correspondentPartner,
        };
    },
});
