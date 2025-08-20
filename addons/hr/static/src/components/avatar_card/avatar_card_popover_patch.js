import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.userInfoTemplate = "hr.avatarCardUserInfos";
    },
    get fieldNames() {
        const fields = super.fieldNames;
        return fields.concat([
            "work_phone",
            "work_email",
            "work_location_id",
            "work_location_type",
            "job_title",
            "department_id",
            this.props.recordModel ? "employee_id" : "employee_ids",
        ]);
    },
    get email() {
        return this.user.work_email || this.user.email;
    },
    get phone() {
        return this.user.work_phone || this.user.phone;
    },
    async getProfileAction() {
        return this.user.employee_ids?.length > 0
            ? this.orm.call("hr.employee", "get_formview_action", [this.user.employee_ids[0]])
            : super.getProfileAction(...arguments);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
