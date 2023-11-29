/** @odoo-module **/

import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

export class AvatarCardEmployeePopover extends AvatarCardResourcePopover {
    async onWillStart() {
        await super.onWillStart();
        this.record.employee_id = [this.props.id];
    }

    get fieldNames() {
        const excludedFields = ["employee_id", "resource_type"];
        return super.fieldNames.filter((field) => !excludedFields.includes(field));
    }
}

AvatarCardEmployeePopover.defaultProps = {
    ...AvatarCardResourcePopover.defaultProps,
    recordModel: "hr.employee",
};
