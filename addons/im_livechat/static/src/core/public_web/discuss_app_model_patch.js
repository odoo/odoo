import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(env);
        this.defaultLivechatCategory = Record.one("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechat",
                    icon: "fa fa-comments",
                    hideWhenEmpty: true,
                    id: `im_livechat.category_default`,
                    name: _t("Livechat"),
                    sequence: 21,
                };
            },
        });
        this.livechats = Record.many("Thread", { inverse: "appAsLivechats" });
    },
});
