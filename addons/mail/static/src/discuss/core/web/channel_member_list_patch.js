import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/ui/popover/popover_hook";
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
                id: member.partner_id.main_user_id?.id,
            });
        }
    },
});
Object.assign(ChannelMemberList.components, { AvatarCardPopover });
