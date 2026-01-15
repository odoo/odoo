import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get placeholder() {
        if (this.env.inFrontendPortalChatter) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },
});
