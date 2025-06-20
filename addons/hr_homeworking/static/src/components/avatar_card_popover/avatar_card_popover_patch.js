import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { patch } from "@web/core/utils/patch";

patch(AvatarCardPopover.prototype, {
    get fieldNames() {
        return [...super.fieldNames, "remote_work_location_type"];
    },
});
