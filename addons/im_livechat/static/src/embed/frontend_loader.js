import { canLoadLivechat } from "@im_livechat/embed/common/misc";
import { loadEditorBundle } from "@html_editor/public/load_editor_bundle";
import { registry } from "@web/core/registry";

// Resolved by `im_livechat.boot` once the lazy loaded livechat services are started.
export const livechatStarted = Promise.withResolvers();

export async function loadLivechatAssets() {
    await loadEditorBundle("im_livechat.assets_embed_frontend");
    await livechatStarted.promise;
}

export const livechatLoaderService = {
    start() {
        if (canLoadLivechat()) {
            loadLivechatAssets();
        }
    },
};
registry.category("services").add("im_livechat.loader", livechatLoaderService);
