import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

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
        return super.showViewProfileBtn || Boolean(this.employee);
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
        return this.orm.call("hr.employee", "get_formview_action", [this.employee.id]);
    },
};
export const unpatchAvatarCard = patch(AvatarCard.prototype, avatarCardPatch);
