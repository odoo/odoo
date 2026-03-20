import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

export class AvatarCardEmployeePopover extends AvatarCardResourcePopover {
    static props = {
        ...AvatarCardResourcePopover.props,
        model: {
            type: String,
            validate: (m) => ["hr.employee", "hr.employee.public"].includes(m),
            optional: true,
        },
    };

    static defaultProps = {
        ...AvatarCardResourcePopover.defaultProps,
        model: "hr.employee",
    };

    get employee() {
        return this.store[this.props.model].get(this.props.id);
    }

    get user() {
        return this.employee?.user_id;
    }

    get name() {
        return this.employee?.name;
    }

    get displayAvatar() {
        return this.employee;
    }
}
