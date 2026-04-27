import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";
import { usePopover } from "@web/core/popover/popover_hook";


export class GanttEmployeeAvatar extends Avatar {
    static template = "hr.GanttEmployeeAvatar";

    setup() {
        super.setup();
        this.avatarCard = usePopover(AvatarCardEmployeePopover);
    }

    openCard(ev) {
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
