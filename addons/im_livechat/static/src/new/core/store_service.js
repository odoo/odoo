/** @odoo-module */

import { Store } from "@mail/new/core/store_service";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, "im_livechat", {
    setup(env) {
        this._super(env);
        this.discuss.livechat = {
            extraClass: "o-mail-category-livechat",
            id: "livechat",
            name: _t("Livechat"),
            isOpen: true,
            canView: false,
            canAdd: false,
            threads: [], // list of ids
        };
    },
});
