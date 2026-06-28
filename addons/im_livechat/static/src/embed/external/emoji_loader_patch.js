import { loadJS } from "@web/core/assets";
import { emojiLoader } from "@web/core/emoji_picker/emoji_loader";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { session } from "@web/session";

patch(emojiLoader, {
    loadEmojiBundle: function loadLiveChatEmojiBundle() {
        return loadJS(
            url("/im_livechat/emoji_bundle", null, {
                origin: session.livechatData.serverUrl,
            })
        );
    },
});
