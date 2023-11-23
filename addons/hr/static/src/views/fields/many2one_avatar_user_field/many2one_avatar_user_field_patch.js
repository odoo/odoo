/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { browser } from "@web/core/browser/browser";
import {
    Many2OneAvatarUserField,
    KanbanMany2OneAvatarUserField,
} from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";

export const patchMany2OneAvatarUserField = {
    setup() {
        super.setup(...arguments);
        if (this.relation === 'hr.employee') {
            this.avatarCard = usePopover(AvatarCardEmployeePopover, {
                closeOnHoverAway: true,
            });
        }
    },

    openCard(ev) {
        if (!this.env.isSmall && this.relation === 'hr.employee') { // TODO: manage mobile view
            const target = ev.currentTarget;
            if (!target.querySelector(":scope > img")) {
                return;
            }
            this.openTimeout = browser.setTimeout(() => {
                if (!this.avatarCard.isOpen) {
                    this.avatarCard.open(target, {
                        id: this.props.record.data[this.props.name][0],
                    });
                }
            }, 350);
        } else {
            return super.openCard(ev);
        }
    },
};

patch(Many2OneAvatarUserField.prototype, patchMany2OneAvatarUserField);
patch(KanbanMany2OneAvatarUserField.prototype, patchMany2OneAvatarUserField);
