import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(...arguments);
        this.livechats = fields.Many("discuss.channel", { inverse: "appAsLivechats" });
        this.isLivechatInfoPanelOpenByDefault = fields.Attr(true, { localStorage: true });
    },
    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        if (nextActiveAction?.id === "livechat-info") {
            return false;
        }
        return super.shouldDisableMemberPanelAutoOpenFromClose(...arguments);
    },
});
