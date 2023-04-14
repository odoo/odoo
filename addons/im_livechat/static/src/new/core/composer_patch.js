/** @odoo-module */

import { Composer } from "@mail/composer/composer";
import { patch } from "@web/core/utils/patch";
import { options } from "../../livechat_data";
import { _t } from "@web/core/l10n/translation";

patch(Composer.prototype, "im_livechat", {
    get allowUpload() {
        return this.thread?.type !== "livechat" && this._super();
    },

    get allowEmojis() {
        return this.thread?.type !== "livechat" && this._super();
    },

    get placeholder() {
        if (this.thread?.type !== "livechat") {
            return this._super();
        }
        return options.input_placeholder || _t("Ask something...");
    },
});
