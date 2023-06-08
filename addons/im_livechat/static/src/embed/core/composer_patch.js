/* @odoo-module */

import { options } from "@im_livechat/embed/livechat_data";

import { Composer } from "@mail/core/common/composer";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, "im_livechat", {
    get placeholder() {
        if (this.thread?.type !== "livechat") {
            return this._super();
        }
        return options.input_placeholder || _t("Say something...");
    },
});
