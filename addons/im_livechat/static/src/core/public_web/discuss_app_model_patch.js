import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import { fields } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(...arguments);
        this.defaultLivechatCategory = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechat",
                    hideWhenEmpty: true,
                    icon: "fa fa-commenting-o",
                    id: `im_livechat.category_default`,
                    name: _t("Livechat"),
                    sequence: 21,
                };
            },
            eager: true,
        });
        this.livechatLookingForHelpCategory = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechatNeedHelp",
                    hideWhenEmpty: true,
                    icon: "fa fa-exclamation-circle",
                    id: `im_livechat.category_need_help`,
                    name: _t("Looking for help"),
                    sequence: 15,
                };
            },
            eager: true,
        });
        this.lastThread = fields.One("Thread");
        this.livechats = fields.Many("Thread", { inverse: "appAsLivechats" });
    },

    _threadOnUpdate() {
        if (this.lastThread?.unpinOnThreadSwitch && this.lastThread.notEq(this.thread)) {
            this.lastThread.isLocallyPinned = false;
        }
        this.lastThread = this.thread;
        super._threadOnUpdate();
    },
});
