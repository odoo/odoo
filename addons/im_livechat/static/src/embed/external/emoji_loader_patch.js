/* @odoo-module */

import { loader } from "@web/core/emoji_picker/emoji_picker";

import { loadBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(loader, {
    loadEmoji: memoize(() =>
        loadBundle({
            jsLibs: [url("/im_livechat/emoji_bundle")],
        })
    ),
});
