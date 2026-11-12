import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { patch } from "@web/core/utils/patch";

patch(AvatarCard.prototype, {
    get phone() {
        return this.partner?.phone_formatted || this.partner?.phone_sanitized || super.phone;
    },
});
