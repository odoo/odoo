import { Many2OneAvatarUserField } from "@mail/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field";
import { patch } from "@web/core/utils/patch";
import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";

patch(Many2OneAvatarUserField.prototype, {
    setup() {
        super.setup(...arguments);
        this.getOutOfOfficeDateEndText = getOutOfOfficeDateEndText;
    },
    get m2oProps() {
        const p = super.m2oProps;
        p.specification = {
            ...p.specification,
            leave_date_to: {},
        };
        return p;
    },
});
