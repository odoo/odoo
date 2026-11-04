import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { Component } from "@odoo/owl";

export class Avatar extends Component {
    static template = "mail.Avatar";
    static props = {
        resModel: { type: String },
        resId: { type: Number },
        displayName: { type: String },
        noSpacing: { type: Boolean, optional: true },
    };

    setup() {
        this.avatarCard = usePopover(AvatarCardPopover);
    }

    onClickAvatar(ev) {
        if (this.env.isSmall || !this.props.resId) {
            return;
        }
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.props.resId,
            });
        }
    }
}
