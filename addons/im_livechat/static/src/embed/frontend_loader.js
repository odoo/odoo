import { canLoadLivechat } from "@im_livechat/embed/common/misc";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

export const livechatLoaderService = {
    start() {
        if (canLoadLivechat()) {
            loadBundle("im_livechat.assets_embed_frontend");
        }
    },
};
registry.category("services").add("im_livechat.loader", livechatLoaderService);
