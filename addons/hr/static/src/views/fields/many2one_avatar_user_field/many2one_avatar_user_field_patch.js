/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import {
    Many2OneAvatarUserField,
    KanbanMany2OneAvatarUserField,
} from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";

export const patchMany2OneAvatarUserField = {
    setup() {
        super.setup(...arguments);
        if (['hr.employee', 'hr.employee.public'].includes(this.relation)) {
            this.avatarCard = usePopover(AvatarCardEmployeePopover, { closeOnClickAway: true });
        }
    },

    onClickAvatar(ev) {
        const id = this.props.record.data[this.props.name][0] ?? false;
        if (id !== false) {
            if (this.env.isSmall || !['hr.employee', 'hr.employee.public'].includes(this.relation)) {
                return super.onClickAvatar(...arguments);
            }
            const target = ev.currentTarget;
            if (!this.avatarCard.isOpen) {
                this.avatarCard.open(target, {
                    id,
                    recordModel: this.relation,
                });
            }
        }
    },
};

patch(Many2OneAvatarUserField.prototype, patchMany2OneAvatarUserField);
patch(KanbanMany2OneAvatarUserField.prototype, patchMany2OneAvatarUserField);
