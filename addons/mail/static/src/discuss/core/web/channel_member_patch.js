import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { useAvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { signal } from "@odoo/owl";

import { patch } from "@web/core/utils/patch";

patch(ChannelMember.prototype, {
    setup() {
        super.setup(...arguments);
        this.isAvatarCardOpen = signal(false);
        this.avatarCard = useAvatarCard({
            model: "res.partner",
            popoverOptions: {
                arrow: false,
                onClose: () => this.isAvatarCardOpen.set(false),
                popoverClass: "mx-2",
                position: "right-start",
            },
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
        if (this.avatarCard.open(ev, memberAtRender.partner_id)) {
            this.isAvatarCardOpen.set(true);
        }
    },
});
