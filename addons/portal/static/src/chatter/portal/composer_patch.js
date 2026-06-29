import { Composer } from "@mail/core/common/composer";
import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { maybePlugin } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatterPlugin = maybePlugin(PortalChatterPlugin);
    },

    get placeholder() {
        if (this.portalChatterPlugin?.inFrontendPortalChatter()) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },

    get showComposerAvatar() {
        return super.showComposerAvatar || (this.compact && this.props.composer.portalComment);
    },
});
