/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";
import {
    Many2ManyTagsAvatarUserField,
    ListMany2ManyTagsAvatarUserField,
    KanbanMany2ManyTagsAvatarUserField,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";

const many2manyAvatarUserPatch = {
    setup() {
        super.setup(...arguments);
        if (["hr.employee", "hr.employee.public"].includes(this.relation)) {
            this.avatarCard = usePopover(AvatarCardEmployeePopover, { closeOnClickAway: true });
        }
    },
    displayAvatarCard(record) {
        return (
            (!this.env.isSmall && ["hr.employee", "hr.employee.public"].includes(this.relation)) ||
            super.displayAvatarCard
        );
    },
    getAvatarCardProps(record) {
        const originalProps = super.getAvatarCardProps(record);
        if (["hr.employee", "hr.employee.public"].includes(this.relation)) {
            return {
                ...originalProps,
                recordModel: this.relation,
            };
        }
        return originalProps;
    },
};

patch(Many2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
patch(KanbanMany2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
patch(ListMany2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
