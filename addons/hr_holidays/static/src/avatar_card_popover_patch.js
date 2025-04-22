import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";

import { patch } from "@web/core/utils/patch";

patch(AvatarCardPopover.prototype, {
    get fieldNames() {
        return [...super.fieldNames, "leave_date_to"];
    },
    get outOfOfficeDateEndText() {
        if (!this.user.leave_date_to) {
            return "";
        }
        return getOutOfOfficeDateEndText(this.user.leave_date_to);
    },
});
