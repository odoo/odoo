import { loader } from "@web/core/emoji_picker/emoji_picker";

import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { session } from "@web/session";

patch(loader, {
    loadEmoji: () =>
        loadJS(
            url("/im_livechat/emoji_bundle", undefined, {
                origin: session.livechatData.serverUrl,
            })
        ),
});
