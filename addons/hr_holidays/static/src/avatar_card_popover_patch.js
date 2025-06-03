import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { getOutOfOfficeDateEndText } from "@hr_holidays/res_partner_model_patch";

import { patch } from "@web/core/utils/patch";

patch(AvatarCardPopover.prototype, {
    get outOfOfficeDateEndText() {
        if (!this.user?.employee_id?.leave_date_to) {
            return "";
        }
        return getOutOfOfficeDateEndText(this.user.employee_id.leave_date_to);
    },
});
