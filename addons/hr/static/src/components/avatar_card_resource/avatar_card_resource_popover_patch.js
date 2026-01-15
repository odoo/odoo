import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { useService } from "@web/core/utils/hooks";
import { TagsList } from "@web/core/tags_list/tags_list";

const patchAvatarCardResourcePopover = {
    setup() {
        super.setup();
        (this.userInfoTemplate = "hr.avatarCardResourceInfos"),
            (this.actionService = useService("action"));
    },
    get fieldNames() {
        return [
            ...super.fieldNames,
            "department_id",
            this.props.recordModel ? "employee_id" : "employee_ids",
            "hr_icon_display",
            "job_title",
            "show_hr_icon_display",
            "work_email",
            "work_location_id",
            "work_phone",
        ];
    },
    get email() {
        return this.record.work_email || this.record.email;
    },
    get phone() {
        return this.record.work_phone || this.record.phone;
    },
    get showViewProfileBtn() {
        return this.record.employee_id?.length > 0;
    },
    async getProfileAction() {
        return await this.orm.call("hr.employee", "get_formview_action", [
            this.record.employee_id[0],
        ]);
    },
};

patch(AvatarCardResourcePopover.prototype, patchAvatarCardResourcePopover);
// Adding TagsList component allows display tag lists on the resource/employee avatar card
// This is used by multiple modules depending on hr (planning for roles and hr_skills for skills)
patch(AvatarCardResourcePopover, {
    components: {
        ...AvatarCardResourcePopover.components,
        TagsList,
    },
});
