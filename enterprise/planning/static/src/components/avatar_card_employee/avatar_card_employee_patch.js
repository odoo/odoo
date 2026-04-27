/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";


const patchAvatarCardEmployeePopover = {
    get fieldNames() {
        const excludedFields = ["role_ids", "default_role_id"];
        return super.fieldNames.filter((field) => !excludedFields.includes(field));
    },
}

patch(AvatarCardEmployeePopover.prototype, patchAvatarCardEmployeePopover)
