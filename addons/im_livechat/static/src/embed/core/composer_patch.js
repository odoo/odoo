/** @odoo-module */

import { Composer } from "@mail/composer/composer";
import { patch } from "@web/core/utils/patch";
import { options } from "@im_livechat/embed/livechat_data";
import { _t } from "@web/core/l10n/translation";

patch(Composer.prototype, "im_livechat", {
    get placeholder() {
        if (this.thread?.type !== "livechat") {
            return this._super();
        }
        return options.input_placeholder || _t("Say something...");
    },
});
