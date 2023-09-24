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
        if (['hr.employee', 'hr.employee.public'].includes(this.relation)) {
            this.avatarCard = usePopover(AvatarCardEmployeePopover, { closeOnClickAway: true });
        }
    },

    getTagProps(record) {
        return {
            ...super.getTagProps(...arguments),
            onImageClicked: (ev) => {
                const supportedModels = ['res.users', 'hr.employee', 'hr.employee.public'];
                const props = {
                    id: record.resId,
                };
                if (['hr.employee', 'hr.employee.public'].includes(this.relation)) {
                    props.recordModel = this.relation;
                }
                if (this.env.isSmall || !supportedModels.includes(this.relation)) {
                    return;
                }
                const target = ev.currentTarget;
                if (
                    !this.avatarCard.isOpen ||
                    (this.lastOpenedId && record.resId !== this.lastOpenedId)
                ) {
                    this.avatarCard.open(target, props);
                    this.lastOpenedId = record.resId;
                }
            },
        };
    }

};

patch(Many2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
patch(KanbanMany2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
patch(ListMany2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
