import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer_model";

patch(Composer.prototype, {
    get syncTextWithMessage() {
        return super.syncTextWithMessage && !this.portalComment;
    },
});
