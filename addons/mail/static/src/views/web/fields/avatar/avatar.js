import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { Component, props, t } from "@odoo/owl";

export const avatarProps = {
    resModel: t.string(),
    resId: t.number(),
    uniqueId: t.number().optional(),
    canOpenPopover: t.boolean().optional(true),
    cssClass: t.or([t.string(), t.object()]).optional(),
    displayName: t.string().optional(),
    noSpacing: t.boolean().optional(),
};

export class Avatar extends Component {
    static template = "mail.Avatar";
    props = props(avatarProps);

    setup() {
        this.avatarCard = usePopover(AvatarCard);
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

    get src() {
        let src = `/web/image/${this.props.resModel}/${this.props.resId}/avatar_128`;
        if (this.props.uniqueId) {
            src += `?unique=${this.props.uniqueId}`;
        }
        return src;
    }

    onClickAvatar(ev) {
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen && this.canOpenPopover) {
            this.avatarCard.open(target, this.popoverProps);
        }
    }
}
