import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { Composer } from "@mail/core/common/composer";
import { maybePlugin } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatter = maybePlugin(PortalChatterPlugin);
    },

    get inFrontendPortalChatter() {
        return this.portalChatter?.inFrontendPortalChatter() ?? false;
    },

    get placeholder() {
        if (this.inFrontendPortalChatter) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },
});
