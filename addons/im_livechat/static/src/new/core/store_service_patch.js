/** @odoo-module */

import { Store } from "@mail/new/core/store_service";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, "im_livechat", {
    setup(env) {
        this._super(env);
        this.discuss.livechat = {
            extraClass: "o-DiscussCategory-livechat",
            id: "livechat",
            name: _t("Livechat"),
            isOpen: false,
            canView: false,
            canAdd: false,
            serverStateKey: "is_discuss_sidebar_category_livechat_open",
            threads: [], // list of ids
        };
    },
});
