import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";

import { patch } from "@web/core/utils/patch";

patch(AvatarCardResourcePopover.prototype, {
    get outOfOfficeDateEndText() {
        return this.employee?.outOfOfficeDateEndText ?? "";
    },
});
