import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

export class AvatarCardEmployeePopover extends AvatarCardResourcePopover {
    static defaultProps = {
        ...AvatarCardResourcePopover.defaultProps,
        recordModel: "hr.employee",
    };
    async onWillStart() {
        await super.onWillStart();
        this.record.employee_id = [this.props.id];
    }

    get fieldNames() {
        let excludedFields = ["employee_id", "resource_type"];
        /* if user is not hr_user, record model is employee.public, then, exclude email and phone
           and share because no idea why we need it.
         */
        if (this.props.recordModel === 'hr.employee.public') {
            excludedFields = excludedFields.concat(["email", "phone"]);
        }
        return super.fieldNames.filter((field) => !excludedFields.includes(field));
    }
}
