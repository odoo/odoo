import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { Component } from "@odoo/owl";

export class Avatar extends Component {
    static template = "mail.Avatar";
    static components = { Popover: AvatarCardPopover };
    static props = {
        resModel: { type: String },
        resId: { type: Number },
        canOpenPopover: { type: Boolean, optional: true },
        cssClass: { type: [String, Object], optional: true },
        displayName: { type: String, optional: true },
        noSpacing: { type: Boolean, optional: true },
    };
    static defaultProps = {
        canOpenPopover: true,
    };

    setup() {
        this.avatarCard = usePopover(this.constructor.components.Popover);
    }

    get canOpenPopover() {
        return this.props.canOpenPopover && !this.env.isSmall && !!this.props.resId;
    }

    get popoverProps() {
        return {
            id: this.props.resId,
            model: this.props.resModel,
        };
    }

    onClickAvatar(ev) {
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen && this.canOpenPopover) {
            this.avatarCard.open(target, this.popoverProps);
        }
    }
}
