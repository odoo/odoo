import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

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
    get employeeCompany() {
        return this.employeeId?.company_id;
    },
    get showViewProfileBtn() {
        return super.showViewProfileBtn && !this.canActivateEmployeeCompany;
    },
    get canActivateEmployeeCompany() {
        if (!this.employeeCompany) {
            return false;
        }
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        if (activeCompanyIds.includes(this.employeeCompany.id)) {
            return false;
        }
        return user.allowedCompanies.map((c) => c.id).includes(this.employeeCompany.id);
    },
    async getProfileAction() {
        if (!this.employeeId) {
            return super.getProfileAction(...arguments);
        }
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        if (!activeCompanyIds.includes(this.employeeCompany.id)) {
            return super.getProfileAction(...arguments);
        }
        return this.orm.call("hr.employee", "get_formview_action", [this.employeeId.id]);
    },
    async onClickViewEmployeeProfile() {
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        user.activateCompanies([...activeCompanyIds, this.employeeCompany.id], { reload: false });
        const action = await this.getProfileAction();
        this.props.close();
        this.actionService.doAction(action);
    },
};

export const unpatchAvatarCardPopover = patch(AvatarCardPopover.prototype, patchAvatarCardPopover);

Object.assign(AvatarCardPopover.components, { Dropdown, DropdownItem });
