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
        if (["hr.employee", "hr.employee.public"].includes(this.relation)) {
            this.avatarCard = usePopover(AvatarCardEmployeePopover, { closeOnClickAway: true });
        }
    },
    get displayAvatarCard() {
        return (
            (!this.env.isSmall && ["hr.employee", "hr.employee.public"].includes(this.relation)) ||
            super.displayAvatarCard
        );
    },
    getAvatarCardProps() {
        const originalProps = super.getAvatarCardProps();
        if (["hr.employee", "hr.employee.public"].includes(this.relation)) {
            return {
                ...originalProps,
                recordModel: this.relation,
            };
        }
        return originalProps;
    },
};

patch(Many2OneAvatarUserField.prototype, patchMany2OneAvatarUserField);
patch(KanbanMany2OneAvatarUserField.prototype, patchMany2OneAvatarUserField);
