import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { useRef } from "@odoo/owl";
import { setupDisplayName } from "../planning_hooks";

export class PlanningEmployeeAvatar extends Avatar {
    static template = "planning.PlanningEmployeeAvatar";

    static props = {
        ...Avatar.props,
        isResourceMaterial: { type: Boolean, optional: true },
        showPopover: { type: Boolean, optional: true },
        resourceColor: { type: Number, optional: true },
    };

    setup() {
        const displayNameRef = useRef("displayName");
        setupDisplayName(displayNameRef);
        this.avatarCard = usePopover(AvatarCardResourcePopover);
    }

    openCard(ev) {
        if (this.env.isSmall || !this.props.showPopover) {
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
