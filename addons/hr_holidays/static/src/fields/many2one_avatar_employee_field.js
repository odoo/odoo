import { Many2OneAvatarEmployeeField } from "@hr/views/fields/many2one_avatar_employee_field/many2one_avatar_employee_field";
import { patch } from "@web/core/utils/patch";
import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";

patch(Many2OneAvatarEmployeeField.prototype, {
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
