import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { useService } from "@web/core/utils/hooks";
import { TagsList } from "@web/core/tags_list/tags_list";
import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";

export const patchAvatarCardResourcePopover = {
    setup() {
        super.setup();
        this.fieldService = useService("field");
    },
    async onWillStart() {
        await super.onWillStart();
        this.employeeFieldInfo = await this.fieldService.loadFields("hr.employee", {
            fieldNames: ["hr_icon_display"],
        });
    },
    get fieldSpecification() {
        const fieldSpec = super.fieldSpecification;
        fieldSpec.employee_id = {
            fields: {
                ...fieldSpec.user_id.fields.employee_id.fields,
                show_hr_icon_display: {},
                hr_icon_display: {},
                im_status: {},
            },
        };
        delete fieldSpec.user_id.fields.employee_id;
        return fieldSpec;
    },
    get displayAvatar() {
        return this.employee && this.props.recordModel && this.props.id;
    },
    get employee() {
        return super.employee?.[0];
    },
    get employeeRecord() {
        const data = this.employee;
        if (!("im_status" in data) && this.user) {
            data.im_status = this.user.im_status;
        }
        return {
            data,
            fields: this.employeeFieldInfo,
        };
    },

    get showViewProfileBtn() {
        return this.employee;
    },
    async getProfileAction() {
        return await this.orm.call("hr.employee", "get_formview_action", [this.employee.id]);
    },
};

export const unpatchAvatarCardResourcePopover = patch(
    AvatarCardResourcePopover.prototype,
    patchAvatarCardResourcePopover
);
// Adding TagsList component allows display tag lists on the resource/employee avatar card
// This is used by multiple modules depending on hr (planning for roles and hr_skills for skills)
AvatarCardResourcePopover.components = {
    ...AvatarCardResourcePopover.components,
    HrPresenceStatus,
    TagsList,
};

AvatarCardResourcePopover.template = "hr.AvatarCardResourcePopover";
