import { getOutOfOfficeDateEndText } from "@hr_holidays/persona_model_patch";

import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

import { patch } from "@web/core/utils/patch";

patch(AvatarCardResourcePopover.prototype, {
    get outOfOfficeDateEndText() {
        if (!this.record.leave_date_to) {
            return "";
        }
        return getOutOfOfficeDateEndText(this.record.leave_date_to);
    },
});
