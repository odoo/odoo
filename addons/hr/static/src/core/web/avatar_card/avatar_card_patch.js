import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(AvatarCard, {
    get allowedModels() {
        return [...super.allowedModels, "hr.employee", "hr.employee.public"];
    },
});
/** @type {AvatarCard} */
const avatarCardPatch = {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },
    /**
     * Whether the employee's company is not active but can be activated by the
     * current user, in which case a dedicated "View Profile" dropdown is shown.
     *
     * @returns {boolean}
     */
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
    /** @override */
    get displayAvatar() {
        return super.displayAvatar || Boolean(this.employee);
    },
    /** @override */
    get email() {
        return this.employee?.work_email || super.email;
    },
    get employee() {
        switch (this.props.model) {
            case "hr.employee":
                return this.store["hr.employee"].get(this.props.id);
            case "hr.employee.public":
                return this.store["hr.employee.public"].get(this.props.id)?.employee_id;
            case "resource.resource":
                return this.resource?.employee_id[0];
        }
        return this.partner?.employee_id;
    },
    /**
     * Company the employee belongs to, if any.
     *
     * @returns {object|undefined}
     */
    get employeeCompany() {
        return this.employee?.company_id;
    },
    /** @override */
    get name() {
        return this.employee?.name || super.name;
    },
    /** @override */
    get phone() {
        return this.employee?.work_phone || super.phone;
    },
    /** @override */
    get resource() {
        if (["hr.employee", "hr.employee.public"].includes(this.props.model)) {
            return this.employee?.resource_id;
        }
        return super.resource;
    },
    /** @override */
    get showViewProfileBtn() {
        return (
            (super.showViewProfileBtn || Boolean(this.employee)) && !this.canActivateEmployeeCompany
        );
    },
    /** @override */
    get user() {
        if (["hr.employee", "hr.employee.public"].includes(this.props.model)) {
            return this.employee?.user_id;
        }
        return super.user;
    },
    /** @override */
    async getProfileAction() {
        if (!this.employee) {
            return super.getProfileAction(...arguments);
        }
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        if (!activeCompanyIds.includes(this.employeeCompany.id)) {
            return super.getProfileAction(...arguments);
        }
        return this.orm.call("hr.employee", "get_record_default_action", [this.employee.id]);
    },
    /**
     * Activate the employee's company before opening its profile, so the
     * employee form can be displayed for a currently inactive company.
     *
     * @returns {Promise<void>}
     */
    async onClickViewEmployeeProfile() {
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        user.activateCompanies([...activeCompanyIds, this.employeeCompany.id], { reload: false });
        const action = await this.getProfileAction();
        this.props.close();
        this.actionService.doAction(action);
    },
};
export const unpatchAvatarCard = patch(AvatarCard.prototype, avatarCardPatch);
