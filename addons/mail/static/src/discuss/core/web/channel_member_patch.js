import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.isAvatarCardOpen = false;
        this.avatarCard = usePopover(AvatarCard, {
            arrow: false,
            onClose: () => (this.state.isAvatarCardOpen = false),
            popoverClass: "mx-2",
            position: "right-start",
        });
    },
    get attClass() {
        return { ...super.attClass, "o-active": this.state.isAvatarCardOpen };
    },
    get isClickable() {
        return this.member.partner_id;
    },
    onClickAvatar(ev) {
        if (!this.isClickable) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: this.member.partner_id.id,
                model: "res.partner",
            });
            this.state.isAvatarCardOpen = true;
        }
    },
});
Object.assign(ChannelMember.components, { AvatarCard });
