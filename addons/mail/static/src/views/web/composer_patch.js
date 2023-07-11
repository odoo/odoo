/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, "web", {
    get placeholder() {
        if (this.thread && this.thread.model !== "discuss.channel") {
            if (this.props.type === "message") {
                return _t("Send a message to followers...");
            } else {
                return _t("Log an internal note...");
            }
        }
        return this._super();
    },
});
