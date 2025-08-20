import { Composer } from "@mail/core/common/composer";

import { useEffect } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Composer.prototype, {
    setup() {
        super.setup();
        useEffect(
            () => {
                if (this.thread?.composerDisabled || this.thread?.chatbot?.isProcessingAnswer) {
                    this.ref.el.blur();
                } else {
                    this.ref.el.focus();
                }
            },
            () => [this.thread?.composerDisabled, this.thread?.chatbot?.isProcessingAnswer]
        );
    },
    get placeholder() {
        if (this.thread?.channel_type !== "livechat") {
            return super.placeholder;
        }
        return session.livechatData.options.input_placeholder || _t("Say something...");
    },
});
