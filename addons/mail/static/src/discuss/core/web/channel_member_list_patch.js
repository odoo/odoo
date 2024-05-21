import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(ChannelMemberList.prototype, {
    setup() {
        super.setup(...arguments);
        this.avatarCard = usePopover(AvatarCardPopover, {
            position: "right",
        });
    },
    onClickAvatar(ev, member) {
        if (!this.canOpenChatWith(member)) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: member.persona.userId,
            });
        }
    },
});
Object.assign(ChannelMemberList.components, { AvatarCardPopover });
