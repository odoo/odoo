import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer_model";

patch(Composer.prototype, {
    get syncHtmlWithMessage() {
        return super.syncHtmlWithMessage && !this.portalComment;
    },
});
