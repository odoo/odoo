import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.userInfoTemplate = "hr.avatarCardUserInfos";
    },
    get email() {
        return this.user?.employee_id?.work_email || this.user?.email || this.partner?.email;
    },
    get phone() {
        return this.user?.employee_id?.work_phone || this.user?.phone || this.partner?.phone;
    },
    get employeeId() {
        return this.user?.employee_id;
    },
    async getProfileAction() {
        if (!this.user?.employee_id) {
            return super.getProfileAction(...arguments);
        }
        return this.orm.call("hr.employee", "get_formview_action", [this.user.employee_id.id]);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
