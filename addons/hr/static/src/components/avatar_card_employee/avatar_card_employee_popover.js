/** @odoo-module **/

import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

export class AvatarCardEmployeePopover extends AvatarCardResourcePopover {
    get fieldSpecification() {
        const fieldSpec = {
            ...super.fieldSpecification,
            ...super.fieldSpecification.employee_id.fields,
        };
        delete fieldSpec.employee_id;
        return fieldSpec;
    }

    get employee() {
        return this.record.data;
    }
}

AvatarCardEmployeePopover.defaultProps = {
    ...AvatarCardResourcePopover.defaultProps,
    recordModel: "hr.employee",
};
