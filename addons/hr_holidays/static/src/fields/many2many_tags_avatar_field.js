import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";
import { patch } from "@web/core/utils/patch";
import { Many2ManyTagsAvatarField } from "@web/views/fields/many2many_tags_avatar/many2many_tags_avatar_field";

patch(Many2ManyTagsAvatarField.prototype, {
    setup() {
        super.setup(...arguments);
        this.getOutOfOfficeDateEndText = getOutOfOfficeDateEndText;
    },
    get specification() {
        const spec = super.specification;
        if (
            ["res.users", "res.partner", "hr.employee", "resource.resource"].includes(
                this.relation
            )
        ) {
            spec.leave_date_to = {};
        }
        return spec;
    },
});
