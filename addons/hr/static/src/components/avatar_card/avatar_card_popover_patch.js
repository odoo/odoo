import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.userInfoTemplate = "hr.avatarCardUserInfos";
    },
    get email() {
        return this.employeeId?.work_email || super.email;
    },
    get phone() {
        return this.employeeId?.work_phone || super.phone;
    },
    get employeeId() {
        return this.partner?.employee_id;
    },
    async getProfileAction() {
        if (!this.employeeId) {
            return super.getProfileAction(...arguments);
        }
        return this.orm.call("hr.employee", "get_formview_action", [this.employeeId.id], {
            context: {
                allow_company_ids: user.context.allowed_company_ids,
            },
        });
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
