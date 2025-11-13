import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    setup() {
        super.setup(...arguments);
        this.avatarCard = usePopover(AvatarCardPopover, {
            arrow: false,
            popoverClass: "mx-2",
            position: "right-start",
        });
    },
    get attClass() {
        return { ...super.attClass, "o-active": this.avatarCard.isOpen };
    },
    onClickAvatar(ev) {
        if (!this.canOpenChat) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: this.member.partner_id.main_user_id?.id,
                channelMember: this.member,
            });
        }
    },
});
Object.assign(ChannelMember.components, { AvatarCardPopover });
