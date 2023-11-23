/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { browser } from "@web/core/browser/browser";
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
            this.avatarCard = usePopover(AvatarCardEmployeePopover, {
                closeOnHoverAway: true,
            });
        }
    },
    getTagProps(record) {
        return {
            ...super.getTagProps(...arguments),
            openCard: (ev) => {
                const supportedModels = ['res.users', 'hr.employee', 'hr.employee.public'];
                if (this.env.isSmall || !supportedModels.includes(this.relation)) {
                    return;
                }
                const target = ev.currentTarget;
                this.openTimeout = browser.setTimeout(() => {
                    if (
                        !this.avatarCard.isOpen ||
                        (this.lastOpenedId && record.resId !== this.lastOpenedId)
                    ) {
                        this.avatarCard.open(target, {
                            id: record.resId,
                        });
                        this.lastOpenedId = record.resId;
                    }
                }, 350);
            },
            clearTimeout: () => {
                browser.clearTimeout(this.openTimeout);
                delete this.openTimeout;
            },
        };
    }

};

patch(Many2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
patch(KanbanMany2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
patch(ListMany2ManyTagsAvatarUserField.prototype, many2manyAvatarUserPatch);
