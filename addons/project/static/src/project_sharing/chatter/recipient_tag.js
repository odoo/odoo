import { RecipientTag } from "@mail/core/web/recipient_tag";
import { patch } from "@web/core/utils/patch";

patch(RecipientTag.prototype, {
    onClick() {
        return;
    },
});
