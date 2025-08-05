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

    async loadAdditionalData() {
        const promises = super.loadAdditionalData();
        this.skills = false;
        if (this.record.employee_skill_ids?.length) {
            promises.push(
                this.orm
                    .read("hr.employee.skill", this.record.employee_skill_ids, ["display_name", "color"])
                    .then((skills) => {
                        this.skills = skills;
                    })
            );
        }
        return promises;
    }

    get fieldNames() {
        const excludedFields = ["employee_id", "resource_type"];
        return [super.fieldNames.filter((field) => !excludedFields.includes(field)), "employee_skill_ids"];
    }

    get hasFooter() {
        return this.skills?.length > 0 || super.hasFooter;
    }

    get skillTags() {
        return this.skills.map(({ id, display_name, color }) => ({
            id,
            text: display_name,
            colorIndex: color,
        }));
    }
}
