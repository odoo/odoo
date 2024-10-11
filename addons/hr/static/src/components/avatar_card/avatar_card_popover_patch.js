import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export const patchAvatarCardPopover = {
    setup() {
        super.setup();
        this.userInfoTemplate = "hr.avatarCardEmployeeInfos";
    },
    get fieldSpecification() {
        return {
            ...super.fieldSpecification,
            employee_id: {
                fields: {
                    work_phone: {},
                    work_email: {},
                    work_location_name: {},
                    work_location_type: {},
                    job_title: {},
                    department_id: {
                        fields: {
                            display_name: {},
                        },
                    },
                },
            },
        };
    },
    get employee() {
        return this.record.data.employee_id;
    },
    get email() {
        return this.employee?.work_email || this.user.email;
    },
    get phone() {
        return this.employee?.work_phone || this.user.phone;
    },
    async onClickViewEmployee() {
        if (!this.employee) {
            return;
        }
        const action = await this.orm.call("hr.employee", "get_formview_action", [
            this.employee.id,
        ]);
        this.actionService.doAction(action);
    },
    async getProfileAction() {
        return this.user.employee_ids?.length > 0
            ? this.orm.call("hr.employee", "get_formview_action", [this.user.employee_ids[0]])
            : super.getProfileAction(...arguments);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);
