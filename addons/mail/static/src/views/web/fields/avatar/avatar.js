import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { Component } from "@odoo/owl";

export class Avatar extends Component {
    static template = "mail.Avatar";
    static props = {
        resModel: { type: String, optional: true },
        resId: { type: Number, optional: true },
        displayName: { type: String, optional: true },
        noSpacing: { type: Boolean, optional: true },
    };

    setup() {
        if (this.props.resModel === "res.users") {
            this.avatarCard = usePopover(AvatarCardPopover);
        }
    }

    onClickAvatar(ev) {
        if (this.env.isSmall || !this.props.resId || this.props.resModel !== "res.users") {
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
