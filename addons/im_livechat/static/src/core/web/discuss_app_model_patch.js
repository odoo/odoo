import { LivechatChannel } from "@im_livechat/core/web/livechat_channel_model";

import { DiscussApp } from "@mail/core/common/discuss_app_model";
import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(env);
        this.livechatThreads = Record.many("Thread", { inverse: "appAsLivechat" });
        this.defaultLivechatCategory = Record.one("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-livechat",
                    hideWhenEmpty: true,
                    id: `im_livechat.category_default`,
                    name: _t("Livechat"),
                    sequence: LivechatChannel.LIVECHAT_SEQUENCE,
                };
            },
        });
    },
});
