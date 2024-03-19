import { loader } from "@web/core/emoji_picker/emoji_picker";

import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { isEmbedLivechatEnabled } from "../common/misc";

patch(loader, {
    loadEmoji(env) {
        if (isEmbedLivechatEnabled(env) && !env.odooHoot) {
            return loadJS(url("/im_livechat/emoji_bundle"));
        }
        return super.loadEmoji(...arguments);
    },
});
