import { loader } from "@mail/utils/common/loader";
import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { session } from "@web/session";

patch(loader.marked, {
    _load: () =>
        loadJS(
            url("/im_livechat/marked_bundle", undefined, {
                origin: session.livechatData.serverUrl,
            })
        ),
});
