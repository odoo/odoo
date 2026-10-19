import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { signal } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    setup() {
        super.setup(...arguments);
        this.isAvatarCardOpen = signal(false);
        this.avatarCard = usePopover(AvatarCard, {
            arrow: false,
            onClose: () => this.isAvatarCardOpen.set(false),
            popoverClass: "mx-2",
            position: "right-start",
        });
    },
    get attClass() {
        return { ...super.attClass, "o-active": this.isAvatarCardOpen() };
    },
    /** @param {import("models").ChannelMember} member */
    isClickable(member) {
        return member.partner_id;
    },
    /**
     * @param {MouseEvent} ev
     * @param {Object} param1
     * @param {import("models").ChannelMember} param1.memberAtRender
     */
    onClickAvatar(ev, { memberAtRender }) {
        if (!this.isClickable(memberAtRender)) {
            return;
        }
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(ev.currentTarget, {
                id: memberAtRender.partner_id.id,
                model: "res.partner",
            });
            this.isAvatarCardOpen.set(true);
        }
    },
});
Object.assign(ChannelMember.components, { AvatarCard });
