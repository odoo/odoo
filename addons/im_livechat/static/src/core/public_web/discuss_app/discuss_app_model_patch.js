import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { fields, patchModel } from "@mail/model/export";

export const discussAppPatch = patchModel(DiscussApp, {
    setup(env) {
        super.setup(...arguments);
        this.livechats = fields.Many("discuss.channel", { inverse: "appAsLivechats" });
        this.isLivechatInfoPanelOpenByDefault = this.localStorage(true);
    },
    shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction) {
        if (nextActiveAction?.id === "livechat-info") {
            return false;
        }
        return super.shouldDisableMemberPanelAutoOpenFromClose(...arguments);
    },
});
