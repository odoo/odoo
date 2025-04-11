import { Many2OneAvatarResourceField } from "@resource_mail/views/fields/many2one_avatar_resource/many2one_avatar_resource_field";
import { patch } from "@web/core/utils/patch";
import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";

patch(Many2OneAvatarResourceField.prototype, {
    setup() {
        super.setup(...arguments);
        this.getOutOfOfficeDateEndText = getOutOfOfficeDateEndText;
    },
});
